"""Check ritual participation at crystal hitbox boundaries against vanilla."""
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-crystal-hitboxes/cases.json'


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
    assert report['vertical_offsets'] == [c['offset'] for c in spec['vertical_cases']]
    base_y = report['portal_y'] + 1
    positions = [[.5, base_y + c['offset'], -2.5] for c in spec['vertical_cases']]
    positions += [[x, base_y, z] for x, z in spec['ordinary_xz']]
    assert report['ritual_crystal_positions'] == positions
    assert len(report['candidate_presence']) == len(positions) - 1
    assert all('Test passed' in raw for raw in report['candidate_presence'])
    packets = report['packets']
    assert sum(p['packet'] == 'ServerboundUseItemOnPacket' for p in packets) == 1
    assert any(p['packet'] == 'ServerboundPlayerLoadedPacket' for p in packets)
    spawns = {}
    for packet in packets:
        text = packet['detail']
        if packet['packet'] != 'ClientboundAddEntityPacket' or 'type=END_CRYSTAL,' not in text:
            continue
        eid = int(re.search(r'entityId=(\d+)', text)[1])
        pos = [float(re.search(rf'\b{axis}=([-\d.]+)', text)[1]) for axis in 'xyz']
        assert eid not in spawns
        spawns[eid] = pos
    assert len(spawns) == len(positions) + 1
    assert sorted(spawns.values()) == sorted(positions + [[.5, base_y, -5.5]])
    center = 'value=Optional[(' + ', '.join(map(str, spec['beam_target'])) + ')]'
    beamed = {int(re.search(r'entityId=(\d+)', p['detail'])[1]) for p in packets
              if p['packet'] == 'ClientboundSetEntityDataPacket'
              and 'id=8,' in p['detail'] and center in p['detail']}
    assert beamed <= spawns.keys()
    cases = []
    for case, pos in zip(spec['vertical_cases'], positions):
        ids = {eid for eid, observed in spawns.items() if observed == pos}
        assert len(ids) == 1
        participates = bool(ids & beamed)
        expected = case['baseline_participates'] if target == 'baseline' else case['participates']
        assert participates == expected, (case['offset'], participates, expected)
        cases.append({'offset': case['offset'], 'participates': participates,
                      'matches_vanilla': participates == case['participates']})
    for x, z in spec['ordinary_xz']:
        ids = {eid for eid, pos in spawns.items() if pos == [x, base_y, z]}
        assert len(ids) == 1 and ids <= beamed
    x, z = spec['control_xz']
    control = {eid for eid, pos in spawns.items() if pos == [x, base_y, z]}
    assert len(control) == 1 and not control & beamed
    return {'cases': cases, 'vanilla_mismatches': sum(not c['matches_vanilla'] for c in cases),
            'beamed': len(beamed), 'spawned': len(spawns), 'ordinary_participants': 3,
            'control_uninvolved': True, 'actual_item_use': True,
            'controlled_ticks': spec['observation_ticks']}


if __name__ == '__main__':
    import sys
    print(json.dumps(check(sys.argv[1], sys.argv[2]), indent=2))
