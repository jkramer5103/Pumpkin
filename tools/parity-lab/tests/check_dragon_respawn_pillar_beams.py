"""Check regenerated pillar beam metadata from isolated vanilla/Pumpkin rituals."""
import hashlib
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-pillar-beams/cases.json'


def check(path, target):
    spec = json.loads(FIXTURE.read_text())
    report = json.loads(Path(path).read_text())
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert report['target'] == target and report['complete'] and report['stopped']
    assert report['client_alive'] and report['player_present']
    assert report['initial_dragon_present'] and report['cleanup_passed']
    assert [r['tick'] for r in report['rows']] == list(range(1, spec['observation_ticks'] + 1))
    clock = lambda key: int(re.search(r'\d+', report[key])[0])
    assert clock('clock_after') - clock('clock_before') == spec['observation_ticks']
    assert not any(any(error in event['raw'] for error in (
        'not loaded', 'Incorrect argument', 'Unknown command', 'Expected whitespace'))
        for event in report['events'])
    observer = re.search(r'\[([^\]]+)\]', report['pillar_observer_position'])[1]
    assert [float(v.strip().removesuffix('d')) for v in observer.split(',')] == [38.5, 100.0, 12.5]
    packets = report['packets']
    assert sum(p['packet'] == 'ServerboundUseItemOnPacket' for p in packets) == 1
    assert any(p['packet'] == 'ServerboundPlayerLoadedPacket' for p in packets)
    entity_id = lambda detail: int(re.search(r'entityId=(\d+)', detail)[1])
    metadata = lambda eid, rows: [p['detail'] for p in rows
        if p['packet'] == 'ClientboundSetEntityDataPacket' and entity_id(p['detail']) == eid]
    center = 'value=Optional[(' + ', '.join(map(str, spec['beam_target'])) + ')]'
    has_center = lambda rows: any('id=8,' in text and center in text for text in rows)
    initial = {entity_id(p['detail']) for row in report['rows'][:2] for p in row['packets']
        if p['packet'] == 'ClientboundSetEntityDataPacket' and has_center([p['detail']])}
    assert len(initial) == 4, initial
    regenerated = []
    for column in spec['pillar_columns']:
        x, z = column
        spawned = [p['detail'] for p in packets
            if p['packet'] == 'ClientboundAddEntityPacket' and 'type=END_CRYSTAL,' in p['detail']
            and f'x={x + .5},' in p['detail'] and f'z={z + .5},' in p['detail']]
        assert len(spawned) == 1, spawned
        detail = spawned[0]
        eid = entity_id(detail)
        assert eid not in initial
        values = metadata(eid, packets)
        # Use the contiguous packet stream: network callbacks can arrive between
        # per-tick snapshots. No later phase can retarget these pillars in 185 ticks.
        beam_values = [text for text in values if 'id=8,' in text]
        beam = bool(beam_values) and has_center(beam_values[:1])
        if target == 'baseline':
            assert not beam and not has_center(values), values
        else:
            assert beam, (column, values)
        reset = metadata(eid, report['reset_packets'])
        if target != 'baseline':
            assert any('id=8,' in text and 'value=Optional.empty' in text for text in reset), reset
        regenerated.append({'column': column, 'center_beam': beam})
    ordinary = [p['detail'] for p in packets if p['packet'] == 'ClientboundAddEntityPacket'
        and 'type=END_CRYSTAL,' in p['detail'] and f"x={spec['ordinary_crystal'][0]}," in p['detail']
        and f"z={spec['ordinary_crystal'][2]}," in p['detail']]
    assert len(ordinary) == 1
    assert not any('id=8,' in text and 'value=Optional[' in text
        for text in metadata(entity_id(ordinary[0]), packets))
    assert report['ordinary_removed'] and report['released_removed']
    uuid = lambda key: re.search(r'UUID: (\[I; [^\]]+\])', report[key])[1]
    assert uuid('second_before') == uuid('second_after_abort')
    for key in ('ordinary_damage', 'abort_damage', 'released_damage'):
        assert re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', report[key]), report[key]
    return {'regenerated': regenerated, 'ordinary_no_beam': True, 'abort_reset': True,
            'controlled_ticks': spec['observation_ticks'], 'directory': report['directory']}
