"""Check captured lead interactions from the bounded Wither regression arena."""

import json
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert len(report['rows']) == 6
    assert {(r['trial'], r['case']) for r in report['rows']} == {
        (trial, case) for trial in (1, 2) for case in ('wither', 'sheep', 'zombie')
    }
    failed = []
    total = 0
    for row in report['rows']:
        assert row['verified_ticks'] == 29
        assert row['entity_id'] > 0
        assert set(row['checks']) == {
            'initial_leads', '5 clear @a minecraft:lead 0',
            '6 execute if entity @e[tag=pp_target,nbt={NoAI:1b}]',
            'interaction_sent', 'link_state', 'client_alive',
            'player_survival', 'target_position', 'no_environment_error',
        }
        for name, passed in row['checks'].items():
            expected_failure = baseline and row['case'] != 'sheep' and (
                name == 'link_state' or name.endswith('clear @a minecraft:lead 0')
            )
            assert passed != expected_failure, (row['trial'], row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['trial'], row['case'], name))
    assert len(failed) == (8 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
