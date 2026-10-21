"""Check Wither hurt/death sound dispatch without changing combat effects."""
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).parents[1] / "fixtures/wither-living-silent/cases.json"


def check_report(report, *, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    expected = {f"{trial}-{case['id']}": case
                for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == list(expected)
    passed = total = 0
    failed, commands, sounds, motions = [], {}, {}, {}
    for row in report['rows']:
        case = expected[row['case']]
        checks = dict(row['checks'])
        details = [p['detail'] for p in row['packets']
                   if p['packet'] in ('ClientboundSoundPacket', 'ClientboundSoundEntityPacket')]
        wither_sounds = [re.search(r'sound=(ENTITY_WITHER_[A-Z_]+),', s)[1]
                        for s in details if 'sound=ENTITY_WITHER_' in s]
        sounds[row['case']] = wither_sounds
        checks['living_sound_dispatch'] = wither_sounds == (
            ['ENTITY_WITHER_' + case['sound'].upper()] if case['sound'] else [])
        checks['sound_volume_pitch'] = all('volume=1.0,' in s and
                                         0.8 <= float(re.search(r'pitch=([^,]+)', s)[1]) <= 1.2
                                         for s in details)
        death_events = [p for p in row['packets'] if p['packet'] == 'ClientboundEntityEventPacket'
                        and f"entityId={row['boss_id']}," in p['detail']
                        and 'event=LIVING_DEATH)' in p['detail']]
        checks['death_animation'] = len(death_events) == int(case['lethal'])
        if not case['lethal']:
            health = re.search(r'entity data: ([0-9.]+)f', row['after_health'])
            checks['damage_applied'] = health is not None and abs(float(health[1]) - 296.32) < 0.001
            motion = re.search(r'\[([^\]]+)\]', row['after_motion'])
            velocity = [float(v.strip().rstrip('dD')) for v in motion[1].split(',')] if motion else []
            checks['knockback_applied'] = (len(velocity) == 3 and abs(velocity[0] - 0.4) < 0.000001
                                           and abs(velocity[1]) < 0.000001 and abs(velocity[2]) < 0.000001)
            motions[row['case']] = velocity
        assert row['verified_ticks'] == 31
        commands[row['case']] = row['gameplay_sha256']
        for name, value in checks.items():
            total += 1
            passed += bool(value)
            if not value:
                failed.append([row['case'], name])
    if not baseline:
        assert not failed, failed
    return dict(passed=passed, total=total, failed=failed, command_sha256=commands,
                sound_sequences=sounds, hurt_motions=motions)


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        result = check_report(json.loads(Path(filename).read_text()))
        print(filename, result['passed'], '/', result['total'])
