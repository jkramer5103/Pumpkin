"""Safety boundaries and real orchestration of finite seeded comparisons."""
import json
import random
import signal
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from lab.fuzz import fuzz, generate, time_budget
from lab.runner import atomic_json, run
from lab.schema import validate_scenario
from test_core_engine import Fixtures, targets


class FuzzTests(unittest.TestCase):
    def test_reproducible_seed_without_global_rng_side_effects(self):
        state = random.getstate()
        first = generate(1901)
        self.assertEqual(first, generate(1901))
        self.assertNotEqual(first, generate(1902))
        self.assertEqual(random.getstate(), state)
        case, actions = first
        validate_scenario(case)
        self.assertEqual([step for action in actions for step in action['steps']], case['steps'])
        self.assertEqual({a['kind'] for a in actions}, {'blocks', 'scoreboard'})

    def test_generated_commands_stay_in_arena_and_avoid_zero_division(self):
        # Parse generated commands independently, replaying arithmetic and cells.
        operations = set()
        for seed in range(20):
            case, actions = generate(seed, 40)
            scores, cells = {}, {(x,z):'air' for x in range(4) for z in range(4)}
            for command in [*case['setup'], *[s['command'] for s in case['steps']]]:
                p = command.split()
                if p[:3] == ['scoreboard','players','set']:
                    scores[p[3]] = int(p[5])
                elif p[:3] in (['scoreboard','players','add'], ['scoreboard','players','remove']):
                    scores[p[3]] += int(p[5]) * (1 if p[2]=='add' else -1)
                elif p[:3] == ['scoreboard','players','operation']:
                    op, a, b = p[5], scores[p[3]], scores[p[6]]
                    operations.add(op)
                    if op in ('/=', '%='): self.assertNotEqual(b, 0)
                    if op == '><': scores[p[3]],scores[p[6]] = b,a
                    elif op == '=': scores[p[3]] = b
                    elif op == '<': scores[p[3]] = min(a,b)
                    elif op == '>': scores[p[3]] = max(a,b)
                    elif op == '+=': scores[p[3]] = a+b
                    elif op == '-=': scores[p[3]] = a-b
                    elif op == '*=': scores[p[3]] = a*b
                    elif op == '/=': scores[p[3]] = divmod(a,b)[0]
                    elif op == '%=': scores[p[3]] = divmod(a,b)[1]
                    self.assertTrue(all(-2**31 <= v < 2**31 for v in scores.values()))
                elif p[0] in ('fill', 'setblock'):
                    x,y,z = map(int,p[1:4]); ex,ey,ez = map(int,p[4:7]) if p[0]=='fill' else (x,y,z)
                    self.assertTrue(0 <= x <= ex <= 3 and 0 <= z <= ez <= 3 and y == ey == 80)
                    self.assertLessEqual((ex-x+1)*(ez-z+1),16)
                    block = p[7] if p[0]=='fill' else p[4]
                    for xx in range(x,ex+1):
                        for zz in range(z,ez+1): cells[(xx,zz)] = block.removeprefix('minecraft:')
                elif p[:4] == ['execute','if','score','#probe']:
                    continue
                elif p[:3] == ['execute','if','score']:
                    self.assertEqual(scores[p[3]], int(p[6]))
                elif p[:3] == ['execute','if','block']:
                    x,y,z = map(int,p[3:6]); self.assertEqual(y,80)
                    self.assertEqual(cells[(x,z)], p[6].removeprefix('minecraft:'))
        self.assertEqual(operations, {'+=','-=','*=','/=','%=','=','<','>','><'})

    def test_limits_reject_before_any_server_connection(self):
        for seed, actions in [(True,12),(-1,12),(2**64,12),(1,3),(1,41)]:
            with self.assertRaises(ValueError): generate(seed,actions)
        for kwargs in ({'seeds':21}, {'seed':2**64-1,'seeds':2}, {'max_seconds':901},
                       {'max_seconds':float('nan')}, {'timeout':6}, {'max_probes':61}):
            with self.assertRaises(ValueError): fuzz('missing', 'missing', **({'seed':0} | kwargs))

    def test_deadline_restores_signal_and_engine_keeps_incomplete_evidence(self):
        previous = signal.getsignal(signal.SIGALRM)
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixtures()
            original = fixture.factory
            def slow(*args, **kwargs):
                client = original(*args, **kwargs)
                command = client.command
                def call(text):
                    if 'execute if score' in text: time.sleep(0.1)
                    return command(text)
                client.command = call
                return client
            with time_budget(0.03):
                path, report, code = run([generate(0,4,'scoreboard')[0]], targets(), temp,
                    client_factory=slow, lock_path=Path(temp)/'lock')
            self.assertEqual(code,2)
            self.assertFalse(report['complete'])
            self.assertEqual(report['error']['kind'],'TimeoutError')
            self.assertFalse(report['results'][0]['confirmed_mismatch'])
            self.assertTrue((path/'report.json').is_file())
            self.assertTrue(any('objectives remove' in cmd for _,cmd in fixture.calls))
        self.assertEqual(signal.getsignal(signal.SIGALRM),previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0,0))

    def test_campaign_persists_actions_and_dispatches_only_confirmed_failures_to_reducer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            atomic_json(root/'targets.json',targets())
            atomic_json(root/'versions.json',{'vanilla':{'version':'synthetic'},'pumpkin':{'version':'synthetic'}})
            calls=[]
            def compare(cases, target_config, output, **kwargs):
                # Use the real engine with honest synthetic transport fixtures.
                fixture=Fixtures()
                original=fixture.factory
                def factory(*args,**options):
                    client=original(*args,**options)
                    client.command=lambda cmd: ('Test passed' if 'execute if score' in cmd else 'OK')
                    return client
                calls.append(cases[0])
                return run(cases,target_config,output,client_factory=factory,lock_path=root/'lock',repeat=kwargs['repeat'])
            with mock.patch('lab.fuzz.run',side_effect=compare), mock.patch('lab.fuzz.shrink_scenario') as shrink:
                directory,state,code=fuzz(root/'targets.json',root/'out',seed=9,seeds=2,actions=4,
                    mode='scoreboard',versions_path=root/'versions.json')
            self.assertEqual(code,0)
            self.assertTrue(state['complete'])
            self.assertEqual(len(calls),2)
            shrink.assert_not_called()
            for seed in (9,10):
                self.assertEqual(json.loads((directory/f'fuzz-{seed}.json').read_text()),generate(seed,4,'scoreboard')[0])
                self.assertTrue((directory/f'fuzz-{seed}-actions.json').is_file())
            self.assertTrue((directory/'replay.txt').is_file())

    def test_confirmed_mismatch_uses_real_reducer_and_replays_both_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            atomic_json(root/'targets.json',targets())
            atomic_json(root/'versions.json',{'vanilla':{'version':'synthetic'},'pumpkin':{'version':'synthetic'}})
            seen=[]
            def compare(cases, config, output, **kwargs):
                def factory(host,port,password,timeout):
                    class Client:
                        def connect(self): pass
                        def close(self): pass
                        def command(self,cmd):
                            seen.append((port,cmd))
                            if 'execute if score' in cmd:
                                return 'Test failed' if port==25586 and '#a ' in cmd else 'Test passed'
                            return 'OK'
                    return Client()
                return run(cases,config,output,repeat=kwargs['repeat'],client_factory=factory,
                    lock_path=root/'lock',reset_commands=kwargs.get('reset_commands',()))
            with mock.patch('lab.fuzz.run',side_effect=compare), mock.patch('lab.shrink.run',side_effect=compare):
                directory,state,code=fuzz(root/'targets.json',root/'out',seed=20,seeds=1,actions=4,
                    mode='scoreboard',versions_path=root/'versions.json',max_probes=30)
            self.assertEqual(code,1)
            self.assertEqual(len(state['failures']),1)
            self.assertTrue(state['failures'][0]['failure_identity'])
            self.assertTrue(state['reductions'][0]['minimized'])
            reduced=Path(state['reductions'][0]['directory'])
            report=json.loads((reduced/'shrink-report.json').read_text())
            self.assertLess(report['step_count'],report['original_step_count'])
            self.assertTrue(report['probes'][-1]['accepted'])
            for probe in report['probes']:
                trial=json.loads((Path(probe['run'])/'report.json').read_text())
                self.assertEqual(len(trial['results'][0]['attempts']),2)
                self.assertEqual(set(trial['results'][0]['attempts'][0]['targets']),{'vanilla','pumpkin'})

    def test_lock_failure_is_saved_without_missing_trial_details_crash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            atomic_json(root/'targets.json',targets())
            atomic_json(root/'versions.json',{'vanilla':{'version':'synthetic'},'pumpkin':{'version':'synthetic'}})
            def unavailable(cases, config, output, **kwargs):
                from lab.runner import process_lock
                with process_lock(root/'lock'):
                    return run(cases,config,output,lock_path=root/'lock',lock_timeout=0.001)
            with mock.patch('lab.fuzz.run',side_effect=unavailable):
                directory,state,code=fuzz(root/'targets.json',root/'out',seed=0,seeds=2,actions=4,
                    mode='scoreboard',versions_path=root/'versions.json')
            self.assertEqual(code,2)
            self.assertEqual(len(state['runs']),1)
            self.assertEqual(state['failures'][0]['classification'],'incomplete')
            self.assertEqual(state['error']['kind'],'RuntimeError')
            self.assertFalse(state['complete'])
