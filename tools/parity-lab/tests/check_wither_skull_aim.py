"""Check the focused Wither close-aim arena report described in the evidence doc."""

import hashlib
import json
import math
from pathlib import Path
import sys


def check_report(report, baseline=False):
    fixture = Path(__file__).parents[1] / 'fixtures/wither-skull-aim/cases.json'
    spec = json.loads(fixture.read_text())
    assert report['fixture_sha256'] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    cases = {f"{trial}-{case['id']}": case
             for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert len(report['rows']) == len(cases)
    assert {row['case'] for row in report['rows']} == cases.keys()
    failed, total = [], 0
    required = {'shot_seen', 'aim', 'origin', 'boss_alive', 'target_alive',
                'player_creative', 'no_environment_error', 'client_alive'}
    for row in report['rows']:
        case = cases[row['case']]
        assert row['expected'] == case['expected'] and row['dx'] == case['dx']
        assert 1 <= row['shot_tick'] <= spec['max_shot_ticks']
        cleanup_ticks = 26 if row is report['rows'][-1] else 0
        assert row['verified_ticks'] == 25 + row['shot_tick'] + cleanup_ticks
        assert row['origin'] == [15.0, 83.0, 15.0]
        x, y, z = row['motion']
        speed = math.sqrt(x*x + y*y + z*z)
        aimed = speed < 1e-8 if case['expected'] == 'zero' else (
            x * case['dx'] > 0 and abs(z) < 1e-8 and abs(y) < speed * .01)
        assert row['checks']['aim'] == aimed
        assert set(row['checks']) == required
        for name, passed in row['checks'].items():
            expected_failure = baseline and case['id'] != 'control' and name == 'aim'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (10 if baseline else 0)
    return {'passed': total-len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
