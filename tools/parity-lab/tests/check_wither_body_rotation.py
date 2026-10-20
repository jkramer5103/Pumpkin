"""Check the focused Wither body-rotation arena report (see its evidence doc)."""

import json
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert len(report['rows']) == 8
    assert {(r['trial'], r['case']) for r in report['rows']} == {
        (trial, case)
        for trial in (1, 2)
        for case in ('east', 'west', 'forward', 'stationary')
    }
    failed = []
    total = 0
    for row in report['rows']:
        assert row['verified_ticks'] == 26
        for name, passed in row['checks'].items():
            expected_failure = baseline and row['case'] in ('east', 'west') and (
                'execute if entity @e[type=minecraft:wither_skull' in name
                or name == 'body_aligned_origins'
            )
            assert passed != expected_failure, (row['trial'], row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['trial'], row['case'], name))
    assert len(failed) == (12 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
