"""Check first-tick Wither skull launches against captured vanilla origins."""

import hashlib
import json
from pathlib import Path
import re
import sys

FIXTURE = Path(__file__).parents[1] / "fixtures/wither-skull-trig/cases.json"


def check_report(report, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    if 'fixture_sha256' in report:
        assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert [e['command'] for e in report['setup']] == spec['setup']
    expected_rows = [(trial, case) for trial in range(1, spec['trials'] + 1)
                     for case in spec['cases']]
    assert len(report['rows']) == len(expected_rows)
    failed = []
    total = 0
    stimuli = {}
    for index, (row, (trial, case)) in enumerate(zip(report['rows'], expected_rows)):
        assert row['case'] == f"{trial}-{case['id']}" and row['scale'] == case['scale']
        commands = [e['command'] for e in row['events'] if e['command'] != 'time query gametime']
        expected = case['commands'] + (spec['final_cleanup'] if index == len(expected_rows) - 1 else [])
        assert commands == expected, (row['case'], commands, expected)
        stimuli[row['case']] = hashlib.sha256(json.dumps(commands).encode()).hexdigest()
        assert row['verified_ticks'] == (52 if index == len(expected_rows) - 1 else 26)
        assert sum(int(c.split()[-1]) for c in commands if c.startswith('tick step ')) == row['verified_ticks']
        checks = dict(row['checks'])
        # The original discovery used a nonexistent response prefix. Check the raw success/value.
        checks['scale_set'] = f"set to {case['scale']}" in row['scale_set']
        positions = [list(map(float, match)) for match in re.findall(
            r'\[(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)[dD]?,\s*(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)[dD]?,\s*(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)[dD]?\]', row['positions_raw'])]
        assert sorted(positions) == row['positions'] and len(positions) == 2
        for head, (position, origin) in enumerate(zip(row['positions'], case['expected_positions'])):
            assert all(abs(a - b) <= spec['tolerance'] for a, b in zip(position[:2], origin[:2]))
            checks[f'head_{head}_origin'] = all(abs(a - b) <= spec['tolerance'] for a, b in zip(position, origin))
        for name, passed in checks.items():
            assert isinstance(passed, bool)
            expected_failure = baseline and name in ('head_0_origin', 'head_1_origin')
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append([row['case'], name])
    assert len(failed) == (12 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed, 'command_sha256': stimuli}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()), '--baseline' in sys.argv)))
