"""Check actual respawn-abort crystal damage and tracked beam boundaries."""
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-pillar-reset/cases.json'


def check(path, target):
    spec = json.loads(FIXTURE.read_text())
    report = json.loads(Path(path).read_text())
    assert report['target'] == target and report['complete'] and report['stopped']
    assert all(report[k] for k in ('client_alive', 'player_present',
                                  'initial_dragon_present', 'cleanup_passed'))
    assert [[c['x'], c['z']] for c in report['columns']] == spec['columns']
    assert len(report['trials']) == len(spec['cases'])
    assert not any(any(error in event['raw'] for error in (
        'not loaded', 'Incorrect argument', 'Unknown command', 'Expected whitespace'))
        for event in report['events'])
    packets = report['packets']
    assert sum(p['packet'] == 'ServerboundUseItemOnPacket' for p in packets) == len(spec['cases'])
    spawns = {}
    for packet in packets:
        text = packet['detail']
        if packet['packet'] != 'ClientboundAddEntityPacket' or 'type=END_CRYSTAL,' not in text:
            continue
        eid = int(re.search(r'entityId=(\d+)', text)[1])
        pos = [float(re.search(rf'\b{axis}=([-\d.]+)', text)[1]) for axis in 'xyz']
        assert eid not in spawns
        spawns[eid] = pos
    results = []
    for trial, case in zip(report['trials'], spec['cases']):
        assert trial['delta'] == case['offset']
        assert trial['cleanup_passed'] and trial['dragon_absent'] and trial['player_present']
        assert 'Test passed' in trial['participant_present']
        clock = lambda key: int(re.search(r'\d+', trial[key])[0])
        assert clock('clock_after') - clock('clock_before') == spec['observation_ticks']
        assert re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', trial['abort_damage'])
        assert len(trial['samples']) == 2
        for index, sample in enumerate(trial['samples']):
            column = report['columns'][index]
            assert sample['axis'] == ('x' if index == 0 else 'z')
            x, z, r = column['x'], column['z'], column['radius']
            expected_pos = ([x-r+case['offset'], 120, z+.5] if index == 0 else
                            [x+.5, 120, z-r+case['offset']])
            assert sample['pos'] == expected_pos
            actual_pos = [float(v) for v in re.findall(r'(-?[0-9]+(?:\.[0-9]+)?)d', sample['position_before'])]
            assert actual_pos == expected_pos, sample
            pos = sample['initial_pos']
            assert pos == [x+.5, column['height']+1, z+.5]
            ids = [eid for eid, observed in spawns.items() if observed == pos]
            assert len(ids) == len(spec['cases']), ids
            eid = ids[trial['trial']]
            beam_packets = [p['detail'] for p in packets
                            if p['packet'] == 'ClientboundSetEntityDataPacket'
                            and f'entityId={eid},' in p['detail'] and 'id=8,' in p['detail']]
            assert beam_packets and 'value=Optional[' in beam_packets[0], beam_packets
            reset = case['baseline_reset'] if target == 'baseline' else case['reset']
            assert ('value=Optional.empty' in beam_packets[-1]) == reset, beam_packets
            for key in ('regenerated', 'present_before', 'present_after_abort'):
                assert 'Test passed' in sample[key], sample
            assert 'invulnerable' in sample['damage_before'].lower(), sample
            assert bool(re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', sample['damage_after'])) == reset, sample
            assert ('Test passed' in sample['present_after_damage']) == (not reset), sample
            if not reset:
                assert 'invulnerable' in sample['damage_after'].lower(), sample
            results.append({'axis': sample['axis'], 'offset': case['offset'],
                            'reset': reset, 'matches_vanilla': reset == case['reset']})
    return {'samples': results, 'vanilla_mismatches': sum(not c['matches_vanilla'] for c in results),
            'regenerated_crystals': len(results), 'actual_item_uses': len(spec['cases']),
            'regeneration_ticks_per_trial': spec['observation_ticks'],
            'beam_and_damage_agree': True, 'controls_passed': True}


if __name__ == '__main__':
    import sys
    print(json.dumps(check(sys.argv[1], sys.argv[2]), indent=2))
