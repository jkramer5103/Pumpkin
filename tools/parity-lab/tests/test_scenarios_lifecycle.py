"""Recovery must preserve blocks and restore usable candidate provenance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from infra import deploy_candidate, provision


class LifecycleTests(unittest.TestCase):
    def test_readiness_preserves_existing_block_and_each_attempt(self):
        class Probe:
            block = 'minecraft:diamond_block'

            def command(self, command):
                if command.startswith('setblock 2 64 2 '):
                    self.block = command.split()[4]
                if command.startswith('gamerule ') and len(command.split()) == 2:
                    return 'currently set to '+provision.RULES[command.split()[1]]
                return 'Test passed'

            def close(self):
                pass

        client = Probe()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(provision, 'RUNTIME', Path(directory)), \
             patch.object(provision, 'ready', return_value=client):
            for _ in range(2):
                provision.control('vanilla', {})
                self.assertEqual(client.block, 'minecraft:diamond_block')
            history = list((Path(directory)/'control-evidence').glob('vanilla-*.json'))
            self.assertEqual(len(history), 2)
            for attempt in history:
                events = json.loads(attempt.read_text())
                self.assertTrue(any(e['command'] == 'gamerule advance_time' for e in events))
                self.assertEqual(attempt.stat().st_mode & 0o777, 0o600)

    def test_failed_manifest_publication_restores_candidate_and_checks_recovery(self):
        for had_dropin in (False, True):
            with self.subTest(had_dropin=had_dropin), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                runtime = root/'runtime'
                (runtime/'pumpkin').mkdir(parents=True)
                (runtime/'downloads').mkdir()
                original_manifest = '{"active_candidate":{"kind":"previous"}}\n'
                (runtime/'manifest.json').write_text(original_manifest)
                config = b'private original configuration\n'
                (runtime/'pumpkin/pumpkin.toml').write_bytes(config)
                (runtime/'pumpkin/world').mkdir()
                (runtime/'pumpkin/world/marker').write_text('existing world')
                credentials = json.dumps({'targets': {'pumpkin': {'password': 'fixture-secret'}}})
                (runtime/'targets.json').write_text(credentials)
                dropin = root/'unit.d/50-source-build.conf'
                previous_dropin = '[Service]\nExecStart=/previous/candidate\n'
                if had_dropin:
                    dropin.parent.mkdir()
                    dropin.write_text(previous_dropin)
                binary = root/'built-pumpkin'
                binary.write_bytes(b'fixture binary')
                calls = []

                def broken_publication(path, text, mode=0o600):
                    provision.write(path, text, mode)
                    if path == runtime/'manifest.json':
                        raise OSError('fixture failure after manifest replacement')

                def control(name, target, **kwargs):
                    calls.append(('ready', name))

                def systemctl(action, *names):
                    calls.append((action, *names))

                with patch.object(deploy_candidate, 'RUNTIME', runtime), \
                     patch.object(deploy_candidate, 'DROPIN', dropin), \
                     patch.object(deploy_candidate, 'write', side_effect=broken_publication), \
                     patch.object(deploy_candidate, 'control', side_effect=control), \
                     patch.object(deploy_candidate, 'systemctl', side_effect=systemctl), \
                     patch.object(deploy_candidate.subprocess, 'check_output', side_effect=['a'*40, '']), \
                     patch.object(deploy_candidate.signal, 'signal'), \
                     patch.object(deploy_candidate.tempfile, 'gettempdir', return_value=directory), \
                     patch('sys.argv', ['deploy', '--binary', str(binary), '--build-command', 'fixture build']):
                    with self.assertRaisesRegex(OSError, 'fixture failure'):
                        deploy_candidate.main()
                self.assertEqual((runtime/'manifest.json').read_text(), original_manifest)
                self.assertEqual((runtime/'pumpkin/pumpkin.toml').read_bytes(), config)
                self.assertEqual((runtime/'targets.json').read_text(), credentials)
                self.assertEqual((runtime/'pumpkin/world/marker').read_text(), 'existing world')
                if had_dropin:
                    self.assertEqual(dropin.read_text(), previous_dropin)
                else:
                    self.assertFalse(dropin.exists())
                self.assertEqual(calls, [
                    ('stop', 'pumpkin'), ('daemon-reload',), ('start', 'pumpkin'), ('ready', 'pumpkin'),
                    ('stop', 'pumpkin'), ('daemon-reload',), ('start', 'pumpkin'), ('ready', 'pumpkin')])


if __name__ == '__main__':
    unittest.main()
