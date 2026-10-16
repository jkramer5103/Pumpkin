"""The simulation oracle must distinguish correct and one-tick-late fluid flow."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from infra import validate_simulation
from infra.catalog import load_catalog
from lab.runner import run

ROOT = Path(__file__).resolve().parents[1]


class SimulationTests(unittest.TestCase):
    def test_water_boundary_oracle_detects_a_late_scheduler(self):
        scenarios = load_catalog(ROOT/'scenarios/simulation')
        targets = {'schema_version': 1, 'minecraft_version': 'fixture', 'targets': {
            name: {'host': '127.0.0.1', 'port': port, 'password': 'fixture'}
            for name, port in [('vanilla', 25585), ('pumpkin', 25586)]}}

        def factory(delay):
            class FluidFixture:
                def __init__(self, host, port, password, timeout):
                    self.delay = delay if port == 25586 else 5
                    self.frozen = False
                    self.time = self.placed = self.score = 0

                def connect(self): pass
                def close(self): pass

                def command(self, command):
                    if command == 'tick query':
                        return 'The game is frozen' if self.frozen else 'The game is running normally'
                    if command == 'tick freeze':
                        self.frozen = True
                        return 'The game is frozen'
                    if command == 'tick unfreeze':
                        self.frozen = False
                        return 'The game is running normally'
                    if command.startswith('tick step '):
                        self.time += int(command.split()[-1])
                        return 'Stepping ticks'
                    if command == 'time query gametime':
                        return f'The game time is {self.time} tick(s)'
                    if command == 'setblock 2 65 2 minecraft:water':
                        self.placed = self.time
                    if command == 'scoreboard players set #probe pp_sim 0':
                        self.score = 0
                    if command.startswith('execute if block '):
                        water = self.time - self.placed >= self.delay
                        # The initial compound predicate and the tick-four probe expect air below.
                        expect_air = '2 64 2 minecraft:air' in command
                        self.score = int(water != expect_air)
                    if command.startswith('execute if score '):
                        return 'Test passed' if self.score == 1 else 'Test failed'
                    return 'Done'
            return FluidFixture

        for delay, expected in [(5, 'pass'), (6, 'different')]:
            with self.subTest(delay=delay), tempfile.TemporaryDirectory() as tmp:
                _, report, code = run(scenarios, targets, Path(tmp)/'runs', repeat=2,
                                      client_factory=factory(delay), lock_path=Path(tmp)/'lock', probe_ticks=True)
                result = report['results'][0]
                self.assertEqual(result['status'], expected)
                self.assertEqual(code, int(delay != 5))
                self.assertEqual(result['confirmed_mismatch'], delay != 5)
                for attempt in result['attempts']:
                    candidate = attempt['targets']['pumpkin']
                    self.assertEqual(candidate['timing']['verified_ticks'], 6)
                    self.assertEqual([o['expectation_met'] for o in candidate['observations']],
                                     [True, True, delay == 5, True])

    def test_simulation_catalog_requires_engine_barriers_and_bounded_arena(self):
        for case in load_catalog(ROOT/'scenarios/simulation'):
            self.assertEqual(sum(s.get('wait_ticks', 0) for s in case['steps']), 6)
            self.assertFalse(any(c.startswith('tick ') for c in case['setup']+case['cleanup']))
            commands = case['setup']+[s['command'] for s in case['steps']]+case['cleanup']
            self.assertFalse(any('sleep' in c or 'random_tick_speed' in c for c in commands))
            self.assertIn('fill 0 63 0 6 72 6 minecraft:air', case['cleanup'])
            self.assertIn('scoreboard objectives remove pp_sim', case['cleanup'])
            for index, step in enumerate(case['steps']):
                if step.get('observe'):
                    self.assertEqual(step['expect_contains'], 'Test passed')
                    self.assertEqual(case['steps'][index-2]['command'], 'scoreboard players set #probe pp_sim 0')
                    self.assertTrue(case['steps'][index-1]['command'].endswith('run scoreboard players set #probe pp_sim 1'))

    def test_launcher_rejects_unbounded_ticks_before_connecting(self):
        case = load_catalog(ROOT/'scenarios/simulation')[0]
        case['steps'][0]['wait_ticks'] = 41
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'case.json').write_text(json.dumps(case))
            with patch.object(validate_simulation, 'run') as execute:
                with self.assertRaises(SystemExit):
                    validate_simulation.main(['--scenarios', tmp])
                execute.assert_not_called()
