"""Crash durability, recovery exclusion, session identity and replay provenance."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from lab.provenance import ProvenanceError, verify_versions
from lab.recovery import recover_run
from lab.runner import LockError, atomic_json, process_lock, run
from lab.schema import SchemaError
from lab.shrink import ShrinkError, load_versions, replay_reproducer, shrink_scenario
from test_core_engine import Fixtures, scenario, targets
from test_core_integration import fixture_pair, fixture_scenario, shrink_inputs


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(temporary)
        self.enterContext(mock.patch.object(tempfile, 'tempdir', temporary))
        self.enterContext(mock.patch.dict(os.environ, {'TMPDIR': temporary}))

    def test_failed_atomic_replace_and_serialization_preserve_original(self):
        path = self.root / 'report.json'
        atomic_json(path, {'complete': False})
        before = path.read_bytes()
        with mock.patch('lab.runner.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                atomic_json(path, {'complete': True})
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ValueError):
            atomic_json(path, {'bad': float('nan')})
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_hard_kill_preserves_inflight_report_and_recovery_never_replays(self):
        with fixture_pair('hang') as (servers, config):
            cases = self.root / 'scenarios'
            cases.mkdir()
            atomic_json(cases / 'case.json', fixture_scenario())
            atomic_json(self.root / 'targets.json', config)
            process = subprocess.Popen([sys.executable, '-m', 'lab', 'run',
                '--targets', str(self.root / 'targets.json'), '--scenarios', str(cases),
                '--output', str(self.root / 'runs'), '--repeat', '2', '--timeout', '2'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                reached = servers[0].probe_requested.wait(5)
                self.assertTrue(reached, process.stderr.read() if process.poll() is not None else 'Probe not reached')
                directory, = (self.root / 'runs').iterdir()
                saved = json.loads((directory / 'report.json').read_text())
                target = saved['results'][0]['attempts'][0]['targets']['vanilla']
                self.assertEqual(target['pending_command']['command'], 'probe')
                self.assertTrue(any(c['command'] == 'create' for c in target['commands']))
                self.assertEqual(saved['summary']['passed'], 0)
                before = (directory / 'report.json').read_bytes()
                with self.assertRaises(LockError):
                    recover_run(directory, lock_timeout=0.01)
                self.assertEqual((directory / 'report.json').read_bytes(), before)
                with self.assertRaisesRegex(SchemaError, 'owner is still alive'):
                    recover_run(directory, lock_path=self.root / 'uncontended-lock')
                process.send_signal(signal.SIGKILL)
                process.communicate(timeout=5)
                transcript = directory / 'transcripts/vanilla.jsonl'
                # Simulate a torn last transcript write as well as a killed worker.
                with transcript.open('ab') as handle:
                    handle.write(b'{"partial":')
                raw = transcript.read_bytes()
                calls = copy.deepcopy([s.commands for s in servers])
                _, report, code = recover_run(directory)
                self.assertEqual(code, 2)
                self.assertEqual(report['state'], 'abandoned')
                self.assertFalse(report['complete'])
                self.assertEqual(report['summary']['error'], 1)
                self.assertEqual(report['recovery']['uncertain_requests'][0]['command'], 'probe')
                self.assertTrue(report['recovery']['transcript_issues'])
                self.assertFalse(report['recovery']['commands_replayed'])
                self.assertEqual(raw, transcript.read_bytes())
                self.assertEqual(calls, [s.commands for s in servers])
                first_recovery = (directory / 'report.json').read_bytes()
                recover_run(directory)
                self.assertEqual(first_recovery, (directory / 'report.json').read_bytes())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_lost_response_survives_successful_cleanup(self):
        from lab.rcon import RconError
        case = scenario()
        command = case['steps'][0]['command']
        fixture = Fixtures({('vanilla', command): RconError('lost reply')})
        _, report, code = run([case], targets(), self.root, client_factory=fixture.factory)
        self.assertEqual(code, 2)
        target = report['results'][0]['attempts'][0]['targets']['vanilla']
        self.assertEqual(target['uncertain_commands'][0]['command'], command)
        self.assertIn(('vanilla', case['cleanup'][0]), fixture.calls)
        self.assertNotIn('pending_command', target)

    def test_interruption_retains_partial_wire_before_cleanup(self):
        fixture = Fixtures()
        factory = fixture.factory
        command = scenario()['steps'][0]['command']
        def partial(*args, **kwargs):
            client = factory(*args, **kwargs)
            original = client.command
            def execute(text):
                if text == command:
                    client.last_wire_bytes = b'partial wire'
                    client.last_response_packets = [b'partial response']
                    raise KeyboardInterrupt()
                return original(text)
            client.command = execute
            return client
        directory, report, code = run([scenario()], targets(), self.root / 'runs', client_factory=partial)
        self.assertEqual(code, 2)
        events = [json.loads(line) for line in (directory / 'transcripts/vanilla.jsonl').read_text().splitlines()]
        error = next(e for e in events if e['event'] == 'error')
        self.assertEqual(error['received_wire_hex'], b'partial wire'.hex())
        self.assertEqual(error['response_packets_hex'], [b'partial response'.hex()])
        self.assertEqual(report['state'], 'interrupted')

    def test_scratch_disconnect_does_not_recreate_world_or_abort_other_target(self):
        binary = self.root / 'fixture-console'
        binary.write_text('''#!/usr/bin/env python3
print('Server is now running', flush=True)
while True:
    command = input()
    if command == 'stop': break
    if command == 'disconnect': break
    if command.startswith('scoreboard players get #parity_fence '):
        print("Unknown scoreboard objective '" + command.split()[-1] + "'", flush=True)
    else: print('OK', flush=True)
''')
        binary.chmod(0o700)
        case = scenario()
        case['setup'] = ['disconnect']
        _, report, code = run([case], targets(), self.root / 'runs', repeat=2,
            client_factory=Fixtures().factory, pumpkin_console=binary, timeout=1)
        self.assertEqual(code, 2)
        self.assertTrue(report['complete'], 'Both trials should finish despite candidate disconnects')
        attempts = report['results'][0]['attempts']
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(a['targets']['vanilla']['completed'] for a in attempts))
        for attempt in attempts:
            errors = attempt['targets']['pumpkin']['errors']
            self.assertTrue(any('cannot preserve the world session' in e['reason'] for e in errors))

    def test_versions_and_world_identity_recorded_and_world_replacement_rejected(self):
        world = self.root / 'world'
        world.mkdir()
        versions = {name: {'version': 'fixture', 'world': {'path': str(world)}}
                    for name in ('vanilla', 'pumpkin')}
        recorded = verify_versions(versions)
        _, report, code = run([scenario()], targets(), self.root / 'runs',
            target_versions=recorded, client_factory=Fixtures().factory)
        self.assertEqual(code, 0)
        self.assertEqual(report['target_versions'], recorded)
        self.assertIn('inode', report['target_versions']['vanilla']['world'])
        world.rename(self.root / 'archived-world')
        world.mkdir()
        fixture = Fixtures()
        with self.assertRaisesRegex(ProvenanceError, 'world directory identity differs'):
            run([scenario()], targets(), self.root / 'runs', target_versions=recorded,
                client_factory=fixture.factory)
        self.assertEqual(fixture.calls, [])

    def test_versions_checked_again_after_waiting_for_engine_lock(self):
        binary = self.root / 'binary'
        binary.write_bytes(b'original')
        versions = {name: {'version': 'fixture', 'binary': str(binary)} for name in ('vanilla', 'pumpkin')}
        from contextlib import contextmanager
        @contextmanager
        def changed_while_waiting(*args):
            binary.write_bytes(b'replaced during lock wait')
            yield
        fixture = Fixtures()
        with mock.patch('lab.runner.process_lock', changed_while_waiting):
            _, report, code = run([scenario()], targets(), self.root / 'runs',
                target_versions=versions, client_factory=fixture.factory)
        self.assertEqual(code, 2)
        self.assertFalse(report['complete'])
        self.assertEqual(fixture.calls, [])

    def test_replay_rejects_rewritten_provenance_before_server_commands(self):
        with fixture_pair() as (servers, config):
            atomic_json(self.root / 'case.json', fixture_scenario())
            atomic_json(self.root / 'targets.json', config)
            directory, report, code = shrink_scenario(self.root / 'case.json', self.root / 'targets.json',
                self.root / 'shrinks', timeout=2, **shrink_inputs(self.root))
            self.assertEqual(code, 0)
            path = directory / 'target-versions.json'
            versions = load_versions(path)
            original_versions = copy.deepcopy(versions)
            versions['pumpkin']['version'] = 'a different candidate'
            atomic_json(path, versions)
            before = copy.deepcopy([s.commands for s in servers])
            with self.assertRaisesRegex(ShrinkError, 'differ from the original evidence'):
                replay_reproducer(directory, self.root / 'targets.json')
            self.assertEqual(before, [s.commands for s in servers])
            atomic_json(path, original_versions)
            for filename, changed in (
                ('reset.json', {'commands': ['a different reset']}),
                ('reproducer.json', {**json.loads((directory / 'reproducer.json').read_text()),
                                     'cleanup': ['a different cleanup']}),
                ('shrink-report.json', {**report, 'console_arena': True}),
            ):
                with self.subTest(filename=filename):
                    file = directory / filename
                    original = file.read_bytes()
                    atomic_json(file, changed)
                    with self.assertRaisesRegex(ShrinkError, 'differs from the verified evidence'):
                        replay_reproducer(directory, self.root / 'targets.json')
                    self.assertEqual(before, [s.commands for s in servers])
                    file.write_bytes(original)

    def test_lock_timeout_retains_scenario_snapshots(self):
        lock = self.root / 'lock'
        with process_lock(lock):
            path, report, code = run([scenario()], targets(), self.root / 'runs',
                client_factory=Fixtures().factory, lock_path=lock, lock_timeout=0)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads((path / 'scenarios/stone-placement.json').read_text()), scenario())


if __name__ == '__main__':
    unittest.main()
