"""Check participation of overlapping crystals in a real respawn ritual."""
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-overlapping-crystals/cases.json'


def check(path, target):
    spec = json.loads(FIXTURE.read_text())
    report = json.loads(Path(path).read_text())
    assert report['target'] == target and report['complete'] and report['stopped']
    assert all(report[k] for k in ('client_alive', 'player_present',
                                  'initial_dragon_present', 'cleanup_passed'))
    assert [r['tick'] for r in report['rows']] == list(range(1, spec['observation_ticks'] + 1))
    clock = lambda key: int(re.search(r'\d+', report[key])[0])
    assert clock('clock_after') - clock('clock_before') == spec['observation_ticks']
    assert 'Test passed' in report['ordinary_present']
    assert re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', report['abort_damage'])
    assert not any(any(error in event['raw'] for error in (
        'not loaded', 'Incorrect argument', 'Unknown command', 'Expected whitespace'))
        for event in report['events'])
    packets = report['packets']
    assert sum(p['packet'] == 'ServerboundUseItemOnPacket' for p in packets) == 1
    assert any(p['packet'] == 'ServerboundPlayerLoadedPacket' for p in packets)
    expected_positions = [[g['xz'][0], report['portal_y'] + 1, g['xz'][1]]
                          for g in spec['groups'] for _ in range(g['count'])]
    assert report['ritual_crystal_positions'] == expected_positions
    spawns = {}
    for packet in packets:
        text = packet['detail']
        if packet['packet'] != 'ClientboundAddEntityPacket' or 'type=END_CRYSTAL,' not in text:
            continue
        eid = int(re.search(r'entityId=(\d+)', text)[1])
        pos = [float(re.search(rf'\b{axis}=([-\d.]+)', text)[1]) for axis in 'xyz']
        assert eid not in spawns
        spawns[eid] = pos
    assert len(spawns) == 8
    center = 'value=Optional[(' + ', '.join(map(str, spec['beam_target'])) + ')]'
    beamed = {int(re.search(r'entityId=(\d+)', p['detail'])[1]) for p in packets
              if p['packet'] == 'ClientboundSetEntityDataPacket'
              and 'id=8,' in p['detail'] and center in p['detail']}
    assert beamed <= spawns.keys()
    groups = []
    for group in spec['groups']:
        x, z = group['xz']
        ids = {eid for eid, pos in spawns.items() if pos == [x, report['portal_y'] + 1, z]}
        assert len(ids) == group['count']
        count = len(ids & beamed)
        assert count == (1 if target == 'baseline' else group['count'])
        groups.append({'xz': group['xz'], 'crystals': len(ids), 'beamed': count})
    x, z = spec['control_xz']
    control = {eid for eid, pos in spawns.items() if pos == [x, report['portal_y'] + 1, z]}
    assert len(control) == 1 and not control & beamed
    return {'groups': groups, 'beamed': len(beamed), 'spawned': len(spawns),
            'control_uninvolved': True, 'actual_item_use': True,
            'controlled_ticks': spec['observation_ticks']}


if __name__ == '__main__':
    import sys
    print(json.dumps(check(sys.argv[1], sys.argv[2]), indent=2))
