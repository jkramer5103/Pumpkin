"""Check initial Wither skull velocity before any projectile flight tick."""
import hashlib
import json
import math
from pathlib import Path
import sys


def check_report(report, baseline=False):
    fixture = Path(__file__).parents[1] / 'fixtures/wither-skull-launch-speed/cases.json'
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
        motion_matches = all(abs(a-b) < 1e-7 for a,b in
                             zip(row['motion'], case['expected_motion']))
        assert row['checks']['launch_motion'] == motion_matches
        expected_speed = (0.95 if baseline else 0.1) if case['id'] != 'coincident' else 0.0
        assert abs(math.sqrt(sum(v*v for v in row['motion'])) - expected_speed) < 1e-7
        if expected_speed:
            assert all(abs(a/expected_speed - b/0.1) < 1e-7 for a,b in
                       zip(row['motion'], case['expected_motion']))
        assert set(row['checks']) == required
        for name, passed in row['checks'].items():
            expected_failure = baseline and case['id'] != 'coincident' and name == 'launch_motion'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (8 if baseline else 0)
    return {'passed': total-len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()),
                                  '--baseline' in sys.argv)))
