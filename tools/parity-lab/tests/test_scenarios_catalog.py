"""Catalog safety/coverage and positive-observation invariants."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ScenarioCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios=[json.loads(p.read_text()) for p in sorted((ROOT/'scenarios').glob('*.json'))]

    def test_distinct_semantic_cases_and_contract_schema(self):
        from lab.schema import validate_scenario
        self.assertGreaterEqual(len(self.scenarios),25)
        ids=set(); sequences=set()
        for scenario in self.scenarios:
            validate_scenario(scenario)
            self.assertNotIn(scenario['id'],ids)
            ids.add(scenario['id'])
            # Removing id/title/notes must not turn cases into renamed duplicates.
            sequence=tuple(scenario['setup'])+tuple(s['command'] for s in scenario['steps'])
            self.assertNotIn(sequence,sequences)
            sequences.add(sequence)
        self.assertTrue({'blocks','block-states','fill','clone','scoreboard','entities','entity-nbt','execute'} <= {s['category'] for s in self.scenarios})

    def test_every_observation_is_a_positive_state_predicate(self):
        for scenario in self.scenarios:
            self.assertEqual(scenario['setup'][0],'tick freeze')
            self.assertEqual(scenario['cleanup'][-1],'tick unfreeze')
            observed=[s for s in scenario['steps'] if s.get('observe')]
            self.assertTrue(observed,scenario['id'])
            for step in observed:
                self.assertEqual(step['expect_contains'],'Test passed')
                self.assertTrue(re.match(r'execute (if|unless) (block|entity|data|score) ',step['command']),scenario['id'])
                self.assertNotIn('run say',step['command'])
                self.assertEqual(step.get('wait_ticks',0),0)

    def test_all_mutation_regions_and_entities_are_bounded(self):
        for scenario in self.scenarios:
            commands=scenario['setup']+[s['command'] for s in scenario['steps']]+scenario['cleanup']
            for command in commands:
                for mutation in re.finditer(r'\b(setblock|fill|clone|positioned) ((?:-?\d+ ){2}-?\d+)',command):
                    positions=[list(map(int,mutation[2].split()))]
                    tail=command[mutation.end():]
                    if mutation[1] in ('fill','clone'):
                        count=2 if mutation[1]=='clone' else 1
                        other=re.match(r'((?: -?\d+){'+str(count*3)+'})',tail)
                        self.assertIsNotNone(other,command)
                        numbers=list(map(int,other[1].split()))
                        positions.extend(numbers[i:i+3] for i in range(0,len(numbers),3))
                    for x,y,z in positions:
                        self.assertTrue(-32<=x<=32 and 48<=y<=96 and -32<=z<=32,command)
                for selector in re.findall(r'@e\[([^\]]*)\]',command):
                    self.assertIn('type=minecraft:marker',selector)
                    self.assertIn('tag=pp',selector)
                    self.assertIn('x=',selector)
                    self.assertIn('y=',selector)
                    self.assertIn('z=',selector)
                    self.assertTrue('dx=' in selector or 'distance=..0.1' in selector,command)
                self.assertNotRegex(command,r'^(stop|op|ban|whitelist|worldborder|reload)\b')

    def test_critical_semantics_are_observed(self):
        by_id={s['id']:s for s in self.scenarios}
        for id,meaning in [('clone-replace-air','minecraft:air'),('clone-masked','minecraft:gold_block'),
                           ('fill-hollow','minecraft:air'),('fill-outline','minecraft:gold_block'),
                           ('score-division-floor','matches -3'),('score-modulo','matches 2'),
                           ('entity-nbt-merge','right:9'),('entity-teleport','Pos:[4.5d,65.0d,4.5d]')]:
            probes=' '.join(s['command'] for s in by_id[id]['steps'] if s.get('observe'))
            self.assertIn(meaning,probes,id)

if __name__=='__main__':
    unittest.main()
