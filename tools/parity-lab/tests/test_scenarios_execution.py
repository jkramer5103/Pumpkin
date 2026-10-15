"""Catalog regressions: no duplicate experiments or unchecked positive probes."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from infra.author_execution_scenarios import execution_cases
from infra.catalog import validate_catalog
from lab.schema import SchemaError

ROOT=Path(__file__).resolve().parents[1]


class ExecutionCatalogTests(unittest.TestCase):
    def test_execution_cases_are_reproducible_and_distinct(self):
        authored=execution_cases()
        self.assertTrue(0<len(authored)<=25)
        validate_catalog(authored)
        for scenario in authored:
            self.assertEqual(scenario,json.loads((ROOT/'scenarios'/(scenario['id']+'.json')).read_text()))
            for step in scenario['steps']:
                if step.get('observe'):
                    self.assertTrue(step['command'].startswith('execute if '),scenario['id'])
                    self.assertEqual(step['expect_contains'],'Test passed')

    def test_renamed_duplicate_is_rejected_even_with_different_expectations(self):
        original=execution_cases()[0]
        renamed=deepcopy(original)
        renamed.update(id='renamed',title='Different title',notes='Different explanation')
        renamed['steps'][-1]['expect_contains']='Different output'
        renamed['cleanup']=[]
        with self.assertRaisesRegex(SchemaError,'duplicate command sequence'):
            validate_catalog([original,renamed])

    def test_duplicate_ids_are_rejected_for_different_commands(self):
        first,second=execution_cases()[:2]
        second['id']=first['id']
        with self.assertRaisesRegex(SchemaError,'duplicate scenario id'):
            validate_catalog([first,second])

    def test_one_positive_probe_cannot_hide_an_unchecked_observation(self):
        scenario=execution_cases()[0]
        scenario['steps'].append({'command':'execute if score missing pp_exec matches 0','observe':True})
        with self.assertRaisesRegex(SchemaError,'every observation needs a positive'):
            validate_catalog([scenario])

    def test_absent_empty_or_nonobserved_positive_probes_are_rejected(self):
        for replacement in [
            [{'command':'say no observation'}],
            [{'command':'say empty','observe':True,'expect_contains':''}],
            [{'command':'say not observed','expect_contains':'Test passed'}],
        ]:
            scenario=execution_cases()[0]
            scenario['steps']=replacement
            with self.assertRaises(SchemaError):
                validate_catalog([scenario])

    def test_unknown_step_fields_are_rejected(self):
        scenario=execution_cases()[0]
        scenario['steps'][0]['expect_success']=True
        with self.assertRaisesRegex(SchemaError,'unknown fields: expect_success'):
            validate_catalog([scenario])


if __name__=='__main__':
    unittest.main()
