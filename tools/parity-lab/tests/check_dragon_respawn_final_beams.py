"""Check final respawn beam recipients from a stepped official/Pumpkin arena."""
import json
from pathlib import Path
import re


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-final-beams/cases.json'


def check(path, target):
    spec = json.loads(FIXTURE.read_text())
    report = json.loads(Path(path).read_text())
    assert report['target'] == target and report['complete'] and report['stopped']
    assert report['client_alive'] and report['player_present']
    assert report['initial_dragon_present'] and report['cleanup_passed']
    assert [r['tick'] for r in report['rows']] == list(range(1, spec['observation_ticks'] + 1))
    clock = lambda key: int(re.search(r'\d+', report[key])[0])
    assert clock('clock_after') - clock('clock_before') == spec['observation_ticks']
    assert not any(any(error in event['raw'] for error in (
        'not loaded', 'Incorrect argument', 'Unknown command', 'Expected whitespace'))
        for event in report['events'])
    assert sum(p['packet'] == 'ServerboundUseItemOnPacket' for p in report['packets']) == 1
    assert any(p['packet'] == 'ServerboundPlayerLoadedPacket' for p in report['packets'])

    beams = []
    for row in report['rows']:
        for packet in row['packets']:
            if packet['packet'] != 'ClientboundSetEntityDataPacket':
                continue
            match = re.search(r'entityId=(\d+),.*id=8,.*value=Optional\[\((-?\d+), (-?\d+), (-?\d+)\)\]', packet['detail'])
            if match:
                entity, x, y, z = map(int, match.groups())
                beams.append((row['tick'], entity, x, y, z))
    center = tuple(spec['center_beam'])
    initial = [b for b in beams if b[0] <= 2 and b[2:] == center]
    portal_ids = {b[1] for b in initial}
    assert len(initial) == len(portal_ids) == spec['respawn_crystals']
    last_pillar = [b for b in beams if 463 <= b[0] <= 464 and b[1] in portal_ids]
    assert len(last_pillar) == spec['respawn_crystals']
    assert all([b[2], b[4]] == spec['last_pillar_xz'] for b in last_pillar)
    assert {b[1] for b in last_pillar} == portal_ids
    assert len({b[2:] for b in last_pillar}) == 1
    final = [b for b in beams if b[0] >= spec['final_phase_entry_tick']]
    returned = [b for b in final if b[1] in portal_ids and b[2:] == center]
    unrelated = [b for b in final if b[1] not in portal_ids]
    failures = []
    if len(returned) != spec['respawn_crystals'] or {b[1] for b in returned} != portal_ids:
        failures.append('portal_crystals_return_to_center')
    if unrelated:
        failures.append('pillar_crystals_unchanged_at_final_entry')
    if target == 'baseline':
        assert failures == ['portal_crystals_return_to_center', 'pillar_crystals_unchanged_at_final_entry']
        assert not returned and len(unrelated) == 10
        assert all(b[2:] == center for b in unrelated)
    else:
        assert not failures, (target, failures, final)
        assert all(b[0] <= spec['final_phase_entry_tick'] + spec['metadata_flush_allowance'] for b in returned)
    return {'passed': 2 - len(failures), 'total': 2, 'failures': failures,
            'portal_ids': sorted(portal_ids), 'last_pillar_beams': last_pillar,
            'final_beams': final, 'controlled_ticks': spec['observation_ticks'],
            'directory': report['directory']}
