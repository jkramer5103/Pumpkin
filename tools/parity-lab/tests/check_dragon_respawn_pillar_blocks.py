"""Check pillar block restoration during isolated vanilla/Pumpkin respawn rituals."""
import hashlib
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-pillar-blocks/cases.json'


def check(path, target):
    spec = json.loads(FIXTURE.read_text())
    report = json.loads(Path(path).read_text())
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert report['target'] == target and report['complete'] and report['stopped']
    assert all(report[k] for k in ('client_alive', 'player_present',
                                  'initial_dragon_present', 'cleanup_passed'))
    assert [row['tick'] for row in report['rows']] == list(range(1, spec['observation_ticks'] + 1))
    clock = lambda key: int(re.search(r'\d+', report[key])[0])
    assert clock('clock_after') - clock('clock_before') == spec['observation_ticks']
    assert not any(any(error in event['raw'] for error in (
        'not loaded', 'Incorrect argument', 'Unknown command', 'Expected whitespace'))
        for event in report['events'])
    packet_path = Path(report['directory']) / 'rotations.jsonl'
    packets = [json.loads(line) for line in packet_path.read_text().splitlines() if line]
    uses = [i for i, p in enumerate(packets) if p['packet'] == 'ServerboundUseItemOnPacket']
    assert len(uses) == 1
    assert any(p['packet'] == 'ServerboundPlayerLoadedPacket' for p in packets)
    packets = packets[uses[0]:]
    assert [[c['x'], c['z']] for c in report['columns']] == spec['columns']
    assert all('Test passed' in report[k] for k in ('third_hole_before', 'third_hole_after'))
    assert re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', report['abort_damage'])
    columns = []
    for column in report['columns']:
        assert 76 <= column['height'] <= 103 and (column['height'] - 76) % 3 == 0
        assert 'Test passed' in column['cap_after'] and 'Test passed' in column['crystal_after']
        assert [s['name'] for s in column['samples']] == [s['name'] for s in spec['sample_cases']]
        assert len({tuple(s['pos']) for s in column['samples']}) == len(spec['sample_cases'])
        passed = []
        missing = []
        for sample, case in zip(column['samples'], spec['sample_cases'], strict=True):
            assert (sample['before'], sample['expected']) == (case['before'], case['after'])
            assert 'Test passed' in sample['setup_raw'], sample
            restored = 'Test passed' in sample['after_expected_raw']
            original = 'Test passed' in sample['after_before_raw']
            if sample['before'] == sample['expected']:
                assert restored and original, sample
            elif target == 'baseline':
                assert original and not restored, sample
                missing.append(sample['name'])
            else:
                assert restored and not original, sample
            passed.append(sample['name'])
        x, z = column['x'], column['z']
        spawned = [p['detail'] for p in packets
                   if p['packet'] == 'ClientboundAddEntityPacket'
                   and 'type=END_CRYSTAL,' in p['detail']
                   and f'x={x + .5},' in p['detail'] and f'z={z + .5},' in p['detail']]
        assert len(spawned) == 1, spawned
        columns.append({'column': [x, z], 'checked_samples': len(passed),
                        'baseline_missing_restorations': missing})
    return {'columns': columns, 'controlled_ticks': spec['observation_ticks'],
            'third_pillar_untouched': True, 'actual_item_use': True,
            'directory': report['directory'],
            'packet_sha256': hashlib.sha256(packet_path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    import sys
    print(json.dumps(check(sys.argv[1], sys.argv[2]), indent=2))
