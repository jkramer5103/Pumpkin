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
            scenario={'id':'disconnect','setup':['tick freeze'],
                      'steps':[{'command':'execute if block 2 64 2 minecraft:stone',
                                'observe':True,'expect_contains':'Test passed'}],
                      'cleanup':['tick unfreeze']}
            (root/'scenarios/disconnect.json').write_text(json.dumps(scenario))
            output=root/'report.json'
            with patch.object(validate_scenarios,'ROOT',root), \
                 patch.object(validate_scenarios,'Rcon',DisconnectingProbe), \
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


if __name__=='__main__':
    unittest.main()
