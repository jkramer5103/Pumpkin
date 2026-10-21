"""Check regenerated crystal protection using isolated vanilla/Pumpkin arenas."""
import json
from pathlib import Path
import re


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-crystal-protection/cases.json'


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
    initial = set()
    for row in report['rows'][:2]:
        for packet in row['packets']:
            if packet['packet'] == 'ClientboundSetEntityDataPacket':
                match = re.search(r'entityId=(\d+),.*id=8,.*value=Optional\[\(0, 128, 0\)\]', packet['detail'])
                if match:
                    initial.add(int(match[1]))
    assert len(initial) == 4, initial
    for key, (x, z) in zip(('first_before', 'second_before'), spec['pillar_columns']):
        assert 'End Crystal has the following entity data:' in report[key]
        assert re.search(r'Pos: \[' + str(x + .5) + r'd, [\d.]+d, ' + str(z + .5) + r'd\]', report[key])
    assert report['ordinary_removed'] and report['released_removed']
    for key in ('ordinary_damage', 'abort_damage', 'released_damage'):
        assert re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', report[key]), (key, report[key])
    # The second crystal is the same surviving entity after abort, not a replacement.
    uuid = lambda key: re.search(r'UUID: (\[I; [^\]]+\])', report[key])[1]
    assert uuid('second_before') == uuid('second_after_abort')
    protected = report['protected_survives'] and report['protected_damage'] == 'Target is invulnerable to the given damage type'
    if target == 'baseline':
        assert not protected and not report['protected_survives']
        assert re.fullmatch(r'Applied 1(?:\.0)? damage to End Crystal', report['protected_damage'])
    else:
        assert protected, report['protected_damage']
    if target == 'vanilla':
        assert 'Invulnerable: 1b' in report['first_before']
        assert 'Invulnerable: 1b' in report['second_before']
        assert 'Invulnerable: 0b' in report['second_after_abort']
    return {'protected': protected, 'ordinary_damage_control': True, 'abort_reset_control': True,
            'controlled_ticks': spec['observation_ticks'], 'directory': report['directory']}
