"""Independent evidence must remain conservative when a probe disconnects."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from infra import validate_scenarios


class ValidationEvidenceTests(unittest.TestCase):
    def test_disconnect_preserves_raw_evidence_without_a_partial_pass(self):
        class DisconnectingProbe:
            def __init__(self,target):
                pass

            def command(self,command):
                if command.startswith('execute'):
                    raise ConnectionError('fixture disconnect')
                return 'raw '+command

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'runtime').mkdir();(root/'scenarios').mkdir()
            (root/'runtime/targets.json').write_text(json.dumps({'targets':{'vanilla':{}}}))
            scenario={'schema_version':1,'id':'disconnect','title':'Disconnect',
                      'category':'blocks','description':'Retain interrupted evidence','tags':['command'],
                      'setup':['tick freeze'],
                      'steps':[{'command':'execute if block 2 64 2 minecraft:stone',
                                'observe':True,'expect_contains':'Test passed'}],
                      'cleanup':['tick unfreeze']}
            (root/'scenarios/disconnect.json').write_text(json.dumps(scenario))
            output=root/'report.json'
            with patch.object(validate_scenarios,'ROOT',root), \
                 patch.object(validate_scenarios,'Rcon',DisconnectingProbe), \
                 patch.object(validate_scenarios.tempfile,'gettempdir',return_value=directory), \
                 patch('sys.argv',['validate','--output',str(output)]):
                with self.assertRaisesRegex(ConnectionError,'fixture disconnect'):
                    validate_scenarios.main()
            report=json.loads(output.read_text())
            self.assertFalse(report['complete'])
            self.assertEqual(report['scenarios'],[scenario])
            result=report['results'][0]
            self.assertFalse(result['complete'])
            self.assertFalse(result['expectations_met'])
            self.assertEqual(result['events'][0]['response'],'raw tick freeze')
            self.assertEqual(result['events'][1]['error'],'ConnectionError: fixture disconnect')
            self.assertEqual(result['events'][2]['response'],'raw tick unfreeze')
            self.assertFalse(output.with_name('report.json.tmp').exists())


    def test_invalid_catalog_is_rejected_before_any_server_commands(self):
        from copy import deepcopy
        from infra.author_execution_scenarios import execution_cases
        from lab.schema import SchemaError

        good=execution_cases()[0]
        unchecked=deepcopy(good)
        unchecked['steps'].append({'command':'say unchecked','observe':True})
        duplicate=deepcopy(good)
        duplicate['id']='renamed-duplicate'
        for catalog in ([unchecked],[good,duplicate]):
            with self.subTest(ids=[s['id'] for s in catalog]), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                (root/'runtime').mkdir();(root/'scenarios').mkdir()
                (root/'runtime/targets.json').write_text(json.dumps({'targets':{'vanilla':{}}}))
                for index,scenario in enumerate(catalog):
                    (root/'scenarios'/f'{index}.json').write_text(json.dumps(scenario))
                output=root/'report.json'
                with patch.object(validate_scenarios,'ROOT',root), \
                     patch.object(validate_scenarios,'Rcon') as client, \
                     patch('sys.argv',['validate','--output',str(output)]):
                    with self.assertRaises(SchemaError):
                        validate_scenarios.main()
                client.assert_not_called()
                self.assertFalse(output.exists())


if __name__=='__main__':
    unittest.main()
