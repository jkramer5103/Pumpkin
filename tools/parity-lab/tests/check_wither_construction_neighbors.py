"""Check Wither construction neighbor notifications against official arena evidence."""

import hashlib
import json
from pathlib import Path
import re
import sys

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-construction-neighbors/cases.json'


def check_report(report, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['shared_engine_lock']
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert [e['command'] for e in report['setup']] == spec['setup']
    expected_rows = [(trial, case) for trial in range(1, spec['trials'] + 1) for case in spec['cases']]
    assert len(report['rows']) == len(expected_rows)
    failures = []
    total = 0
    stimuli = {}
    for row, (trial, case) in zip(report['rows'], expected_rows):
        assert row['case'] == f"{trial}-{case['id']}"
        commands = [e['command'] for e in row['events'] if e['command'] != 'time query gametime']
        assert commands.count('tick step 6') == 4
        assert commands.count('tick step 25') == 1
        assert row['verified_ticks'] == 49
        assert sum(int(c.split()[-1]) for c in commands if c.startswith('tick step ')) == 49
        bud = [case['under'], 80, 15] if case['axis'] == 'x' else [15, 80, case['under']]
        assert row['dispenser'] == bud
        inventory_command = 'data get block ' + ' '.join(map(str, bud))
        counts = [int(re.search(r'count: (\d+)', e['raw'])[1])
                  for e in row['events'] if e['command'] == inventory_command]
        assert counts == [row['before_count'], row['after_count'], row['control_count']]
        assert row['before_count'] == 2
        assert row['control_count'] == (1 if case['powered'] else 2)
        stimuli[row['case']] = hashlib.sha256(json.dumps(commands).encode()).hexdigest()
        assert stimuli[row['case']] == row['gameplay_sha256']
        for name, passed in row['checks'].items():
            assert passed is True, (row['case'], name)
            total += 1
        wakes = case['powered'] and case['complete']
        outcomes = {
            'construction_trigger': row['after_triggered'] == wakes,
            'construction_dispense': row['after_count'] == (1 if wakes else 2),
            'ejected_item': row['ejected_item'] == wakes,
        }
        expected_failures = list(outcomes) if baseline and wakes else []
        failed = [name for name, passed in outcomes.items() if not passed]
        assert failed == expected_failures, (row['case'], failed)
        failures.extend([row['case'], name] for name in failed)
        total += len(outcomes)
    return {'passed': total - len(failures), 'total': total,
            'failed': failures, 'command_sha256': stimuli}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()), '--baseline' in sys.argv)))
