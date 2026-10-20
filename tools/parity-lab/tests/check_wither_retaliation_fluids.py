"""Validate the bounded Wither fluid-retention comparison capture."""

import json
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == [
        'water', 'lava', 'seagrass', 'dry_stairs',
    ]
    failed = []
    total = 0
    for row in report['rows']:
        assert row['verified_ticks'] == 45
        assert len(row['checks']) == 10
        assert row['checks']['damage_applied']
        assert row['checks']['client_alive']
        assert row['checks']['no_environment_error']
        for name, passed in row['checks'].items():
            expected_failure = baseline and row['case'] != 'dry_stairs' and (
                name.startswith('11 execute if block 14 81 14 ')
            )
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (3 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
