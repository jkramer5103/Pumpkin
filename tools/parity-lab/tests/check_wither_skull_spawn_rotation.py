"""Check skull spawn rotation before the first projectile flight tick."""
import hashlib
import json
import math
from pathlib import Path
import re
import sys


def rotation(raw):
    values = re.findall(r'\[(-?[\d.]+)f,\s*(-?[\d.]+)f\]', raw)
    assert len(values) == 1, raw
    return list(map(float, values[0]))


def check_report(report, baseline=False):
    fixture = Path(__file__).parents[1] / 'fixtures/wither-skull-spawn-rotation/cases.json'
    spec = json.loads(fixture.read_text())
    assert report['fixture_sha256'] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    cases = {f"{trial}-{case['id']}": case
             for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert len(report['rows']) == len(cases)
    assert {row['case'] for row in report['rows']} == cases.keys()
    required = {'shot_seen', 'launch_motion', 'origin', 'boss_alive', 'target_alive',
                'player_creative', 'no_environment_error', 'client_alive'}
    failed, total = [], 0
    for row in report['rows']:
        case = cases[row['case']]
        assert row['offset'] == case['offset']
        assert row['expected_motion'] == case['expected_motion']
        assert row['origin'] == [15.0, 83.0, 15.0]
        assert 1 <= row['shot_tick'] <= spec['max_shot_ticks']
        cleanup_ticks = 26 if row is report['rows'][-1] else 0
        assert row['verified_ticks'] == 25 + row['shot_tick'] + cleanup_ticks
        assert len(row['motion']) == 3 and all(math.isfinite(v) for v in row['motion'])
        assert all(abs(a-b) < 1e-7 for a, b in zip(row['motion'], case['expected_motion']))
        assert set(row['checks']) == required
        checks = dict(row['checks'])
        checks['initial_nbt_rotation'] = rotation(row['skull_rotation_raw']) == [37.0, -17.0]
        teleports = [e for e in row['events']
                     if e['command'].startswith('tp @e[tag=pp_boss,limit=1]')]
        assert len(teleports) == row['shot_tick']
        assert all(e['command'] == 'tp @e[tag=pp_boss,limit=1] 15.0 80.0 15.0 37 -17'
                   for e in teleports)
        skulls = [p['detail'] for p in row['packets']
                  if p['packet'] == 'ClientboundAddEntityPacket'
                  and 'type=WITHER_SKULL,' in p['detail']
                  and 'x=15.0, y=83.0, z=15.0,' in p['detail']]
        checks['main_head_spawn_packet'] = len(skulls) == 1
        angles = [{axis: float(re.search(r'(?<![A-Za-z])' + axis + r'=([-\d.]+)', p)[1])
                   for axis in ('yaw', 'pitch', 'headYaw')} for p in skulls]
        # Official 26.3 capture: shooter rotation, packed into signed byte angles.
        checks['initial_packet_rotation'] = angles == [{'yaw': 36.5625, 'pitch': -18.28125, 'headYaw': 0.0}]
        for name, passed in checks.items():
            expected_failure = baseline and name in {'initial_nbt_rotation', 'initial_packet_rotation'}
            assert passed != expected_failure, (row['case'], name, passed, angles)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (20 if baseline else 0)
    return {'passed': total-len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()),
                                  '--baseline' in sys.argv)))
