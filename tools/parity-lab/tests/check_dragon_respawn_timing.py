"""Check the first 105 ticks of an isolated official 26.3 dragon respawn.

The report comes from a real item-use client and frozen-server tick stepping.
No server, credentials, or Minecraft implementation is included in this checker.
"""
import json
from pathlib import Path
import re


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-timing/cases.json'


def check(path, target):
    spec = json.loads(FIXTURE.read_text())
    report = json.loads(Path(path).read_text())
    assert report['target'] == target and report['complete'] and report['stopped']
    assert report['client_alive'] and report['player_present']
    assert report['initial_dragon_present'] and report['cleanup_passed']
    assert len(report['rows']) == spec['observation_ticks']
    assert [r['tick'] for r in report['rows']] == list(range(1, 106))
    clock = lambda key: int(re.search(r'\d+', report[key])[0])
    assert clock('clock_after') - clock('clock_before') == spec['observation_ticks']
    position = report['observer_position'].rsplit('[', 1)[1].rstrip(']')
    assert float(position.split(',')[1].strip().rstrip('d')) == 100.0
    assert not any(any(error in event['raw'] for error in (
        'not loaded', 'Incorrect argument', 'Unknown command', 'Expected whitespace'))
        for event in report['events'])
    assert sum(p['packet'] == 'ServerboundUseItemOnPacket'
               for p in report['packets']) == 1
    assert any(p['packet'] == 'ServerboundPlayerLoadedPacket'
               for p in report['packets'])

    roars, beams = [], []
    for row in report['rows']:
        for packet in row['packets']:
            detail = packet['detail']
            if packet['packet'] == 'ClientboundLevelEventPacket' and 'ANIMATION_DRAGON_SUMMON_ROAR' in detail:
                assert 'position=(0, 128, 0)' in detail
                roars.append(row['tick'])
            if packet['packet'] == 'ClientboundSetEntityDataPacket':
                match = re.search(r'entityId=(\d+),.*id=8,.*value=Optional\[\((-?\d+), (-?\d+), (-?\d+)\)\]', detail)
                if match:
                    entity, x, y, z = map(int, match.groups())
                    beams.append((row['tick'], entity, x, y, z))
    central = [beam for beam in beams if beam[2:] == (0, 128, 0)]
    assert len(central) == 4 and len({beam[1] for beam in central}) == 4
    pillars = [beam for beam in beams if beam[2] == spec['first_pillar_beam_x']
               and beam[4] == spec['first_pillar_beam_z']]
    failures = []
    if roars != spec['expected_preparing_roar_ticks']:
        failures.append('preparing_roar_timing')
    if len(pillars) != 4:
        failures.append('first_pillar_beam')
    else:
        assert {beam[1] for beam in pillars} == {beam[1] for beam in central}
        assert len({beam[2:] for beam in pillars}) == 1
        # Pumpkin flushes dirty entity metadata on the next entity tick.
        # Require the time-zero side effect by the following flush without
        # claiming that this independent packet scheduling difference is fixed.
        assert all(spec['expected_first_pillar_beam_tick'] <= beam[0]
                   <= spec['expected_first_pillar_beam_tick'] + 1 for beam in pillars)
    if target == 'baseline':
        assert roars == spec['baseline_preparing_roar_ticks'] and not pillars
        assert failures == ['preparing_roar_timing', 'first_pillar_beam']
    else:
        assert not failures, (target, failures, roars, pillars)
    return {'passed': 2 - len(failures), 'total': 2, 'failures': failures,
            'roar_ticks': roars, 'pillar_beams': pillars,
            'central_beams': central, 'controlled_ticks': spec['observation_ticks'],
            'portal_y': report['portal_y'], 'directory': report['directory']}
