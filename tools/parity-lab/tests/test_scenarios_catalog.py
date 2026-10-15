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
        self.assertGreaterEqual(len(self.scenarios),50)
        ids=set(); sequences=set()
        for scenario in self.scenarios:
            validate_scenario(scenario)
            self.assertNotIn(scenario['id'],ids)
            ids.add(scenario['id'])
            # Removing id/title/notes must not turn cases into renamed duplicates.
            sequence=tuple(scenario['setup'])+tuple(s['command'] for s in scenario['steps'])
            self.assertNotIn(sequence,sequences)
            sequences.add(sequence)
        self.assertTrue({'blocks','block-states','block-predicates','fill','clone','scoreboard','entities','entity-nbt','execute'} <= {s['category'] for s in self.scenarios})

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
                    self.assertRegex(selector,r'^type=minecraft:(marker|armor_stand),')
                    self.assertIn('tag=pp',selector)
                    self.assertIn('x=',selector)
                    self.assertIn('y=',selector)
                    self.assertIn('z=',selector)
                    coordinates={k:float(v) for k,v in re.findall(r'(x|y|z|dx|dy|dz)=(-?\d+(?:\.\d+)?)',selector)}
                    if 'dx' in coordinates:
                        for axis,low,high in [('x',-32,32),('y',48,96),('z',-32,32)]:
                            start=coordinates[axis]; delta=coordinates.get('d'+axis,0)
                            self.assertTrue(low<=start+min(delta,0)<=start+max(delta,0)<=high,command)
                    else:
                        radius=re.search(r'distance=(?:\d+(?:\.\d+)?)?\.\.(\d+(?:\.\d+)?)',selector)
                        self.assertIsNotNone(radius,command)
                        radius=float(radius[1])
                        for axis,low,high in [('x',-32,32),('y',48,96),('z',-32,32)]:
                            self.assertTrue(low<=coordinates[axis]-radius<=coordinates[axis]+radius<=high,command)
                self.assertNotRegex(command,r'^(stop|op|ban|whitelist|worldborder|reload)\b')

    def test_critical_semantics_are_observed(self):
        by_id={s['id']:s for s in self.scenarios}
        for id,meaning in [('clone-replace-air','minecraft:air'),('clone-masked','minecraft:gold_block'),
                           ('fill-hollow','minecraft:air'),('fill-outline','minecraft:gold_block'),
                           ('score-division-floor','matches -3'),('score-modulo','matches 2'),
                           ('entity-nbt-merge','right:9'),('entity-teleport','Pos:[4.5d,65.0d,4.5d]'),
                           ('predicate-partial-state','unless block 2 64 2 minecraft:oak_stairs[half=bottom]'),
                           ('predicate-tag-state','#minecraft:logs[axis=x]'),
                           ('fill-tag-filter','if block 2 64 0 minecraft:stone if block 3 64 0 minecraft:air'),
                           ('clone-state-filter','if block 5 64 0 minecraft:gold_block'),
                           ('clone-block-entity-nbt','count:3'),
                           ('clone-masked-move','if block 5 64 0 minecraft:gold_block'),
                           ('clone-overlap-normal-preserves','if block 2 64 0 minecraft:air')]:
            probes=' '.join(s['command'] for s in by_id[id]['steps'] if s.get('observe'))
            self.assertIn(meaning,probes,id)

    def test_container_replacement_proves_initial_data_before_clearing_it(self):
        scenario=next(s for s in self.scenarios if s['id']=='block-entity-replacement-clears-nbt')
        observations=[(i,s) for i,s in enumerate(scenario['steps']) if s.get('observe')]
        self.assertEqual(len(observations),2)
        self.assertIn('count:3',observations[0][1]['command'])
        self.assertIn('unless data block 2 64 2 Items[0]',observations[1][1]['command'])
        middle=scenario['steps'][observations[0][0]+1:observations[1][0]]
        self.assertIn({'command':'setblock 2 64 2 minecraft:stone'},middle)

    def test_entity_fixture_coordinates_and_cleanup(self):
        for scenario in self.scenarios:
            commands=scenario['setup']+[s['command'] for s in scenario['steps']]+scenario['cleanup']
            summoned=[]
            for command in commands:
                match=re.match(r'summon minecraft:(marker|armor_stand) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) ',command)
                if match:
                    kind=match[1];x,y,z=map(float,match.groups()[1:])
                    self.assertTrue(-32<=x<=32 and 48<=y<=96 and -32<=z<=32,command)
                    self.assertIn('Tags:["pp"',command)
                    summoned.append(kind)
            for kind in summoned:
                self.assertTrue(any(f'run kill @e[type=minecraft:{kind},tag=pp,' in c for c in scenario['cleanup']),scenario['id'])

    def test_tag_intersection_observes_both_branches(self):
        scenario=next(s for s in self.scenarios if s['id']=='tag-intersection')
        self.assertTrue(any('x=4.5,y=64,z=2.5,distance=..0.1' in s['command'] for s in scenario['steps']))
        probes=' '.join(s['command'] for s in scenario['steps'] if s.get('observe'))
        self.assertIn('tag=excluded,tag=!selected',probes)

if __name__=='__main__':
    unittest.main()
