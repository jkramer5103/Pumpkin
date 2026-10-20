"""Check the sealed-arena Wither idle flight regression report."""

import json
import math
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == [
        f'{trial}-{case}' for trial in (1, 2)
        for case in ('active', 'noai', 'spawn')
    ]
    failed = []
    total = 0
    for row in report['rows']:
        active = row['case'].endswith('-active')
        assert row['verified_ticks'] == (505 if active else 105)
        assert len(row['positions']) == (12 if active else 2)
        assert all(len(pos) == 3 and all(math.isfinite(v) for v in pos) for pos in row['positions'])
        assert len(row['checks']) == (19 if active else 9)
        for name, passed in row['checks'].items():
            expected_failure = baseline and active and name == 'horizontal_flight'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (2 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
