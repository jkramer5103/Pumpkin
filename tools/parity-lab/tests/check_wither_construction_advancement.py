"""Check Wither construction awards and range controls against vanilla evidence."""

import hashlib
import json
from pathlib import Path
import sys

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-construction-advancement/cases.json'


def check_report(report, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert [e['command'] for e in report['setup']] == spec['setup']
    expected = [(trial, case) for trial in range(1, spec['trials'] + 1)
                for case in spec['cases']]
    assert len(report['rows']) == len(expected)
    failures = []
    total = 0
    stimuli = {}
    for row, (trial, case) in zip(report['rows'], expected):
        assert row['case'] == f"{trial}-{case['id']}" and row['mode'] == case['mode']
        commands = [e['command'] for e in row['events'] if e['command'] != 'time query gametime']
        assert 'tp @a ' + ' '.join(str(v) for v in case['position']) in commands
        assert commands.count('advancement grant @a only minecraft:nether/summon_wither') == 1
        if case['mode'] == 'command':
            assert commands.count('summon minecraft:wither 15.5 81.55 15.5 {NoAI:1b,Invul:220,Silent:1b}') == 1
        else:
            assert commands.count('setblock 16 83 17 minecraft:redstone_block') == 1
            assert commands.count('item replace block 16 83 16 container.0 with minecraft:wither_skeleton_skull') == 1
        stimuli[row['case']] = hashlib.sha256(json.dumps(commands).encode()).hexdigest()
        assert stimuli[row['case']] == row['gameplay_sha256']
        assert row['verified_ticks'] == (25 if case['mode'] == 'command' else 31)
        assert sum(int(c.split()[-1]) for c in commands if c.startswith('tick step ')) == row['verified_ticks']
        # Revoking only succeeds when the actual advancement criterion was awarded.
        awarded = 'Revoked the advancement' in row['advancement_raw']
        assert awarded == row['awarded']
        assert row['checks']['advancement_awarded'] == (awarded == case['award'])
        grants = [i for i, e in enumerate(row['events'])
                  if e['command'].startswith('advancement grant ')]
        assert len(grants) == 1
        positive = row['events'][grants[0] + 1]
        assert positive['command'].startswith('advancement revoke ')
        assert 'Revoked the advancement' in positive['raw']
        for name, passed in row['checks'].items():
            assert isinstance(passed, bool)
            expected_failure = baseline and name == 'advancement_awarded' and case['award']
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failures.append([row['case'], name])
    assert len(failures) == (6 if baseline else 0)
    return {'passed': total - len(failures), 'total': total,
            'failed': failures, 'command_sha256': stimuli}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()), '--baseline' in sys.argv)))
