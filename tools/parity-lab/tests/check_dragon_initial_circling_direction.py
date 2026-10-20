"""Check first-circling turns against captured vanilla 26.3 output."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'lab/examples/dragon-initial-circling-direction.json'


def check(report_path, target):
    report = json.loads(Path(report_path).read_text())
    assert report['complete'], 'incomplete arena'
    run = report['targets'][target]
    assert run['stopped'], 'scratch server still running'
    row, = run['attempts']
    assert row['sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    scenario = json.loads(FIXTURE.read_text())
    commands = scenario['setup'] + [step['command'] for step in scenario['steps']] + scenario['cleanup']
    events = iter(row['events'])
    captured = [next(event for event in events if event['command'] == command) for command in commands]
    assert captured[-1]['raw'].strip() == 'Test passed', 'boss cleanup failed'
    checks = dict(row['checks'])
    assert all(checks.values()), 'arena controls failed'
    # Existing steering/trigonometry differences remain below these tolerances;
    # the wrong direction differs by 1.9 degrees and about .002 blocks.
    yaws = []
    for field in ['Rotation', 'Pos', 'Motion']:
        snapshots = [event for event in captured if event['command'].endswith('] ' + field)]
        assert len(snapshots) == 8
        for index, event in enumerate(snapshots):
            match = re.search(r'\[([^\[\]]+)\]$', event['raw'].strip())
            assert match, event
            values = [float(value.strip().rstrip('dDfF')) for value in match[1].split(',')]
            assert len(values) == (2 if field == 'Rotation' else 3)
            if field == 'Rotation':
                yaws.append(values[0])
                checks[f'dragon {index} initial circling yaw'] = abs(values[0] - -1.5735644) < 1e-5
            elif field == 'Pos':
                checks[f'dragon {index} initial horizontal movement'] = abs(values[0] - 39.9983552) < 5e-6
                checks[f'dragon {index} vertical control'] = abs(values[1] - 159.99399999976157) < 1e-10
            else:
                checks[f'dragon {index} initial horizontal velocity'] = abs(values[0] - -.00156197) < 5e-6
                checks[f'dragon {index} vertical velocity control'] = abs(values[1] - -.005460000374317176) < 1e-10
    failures = [name for name, passed in checks.items() if not passed]
    if target == 'baseline':
        assert any(abs(yaw + 3.5) < 1e-6 for yaw in yaws), yaws
        assert failures and all('initial ' in name for name in failures), failures
    else:
        assert not failures, failures
    assert sum(name.endswith('tick delta') for name in checks) == 14
    return dict(target=target, report=str(report_path), passed=sum(checks.values()), total=len(checks),
                failures=failures, yaws=yaws, ticks=sum(step.get('wait_ticks', 0) for step in scenario['steps']),
                fixture_sha256=row['sha256'], stimulus_sha256=hashlib.sha256(json.dumps(commands).encode()).hexdigest(),
                stopped=run['stopped'], binary=run.get('binary'), binary_sha256=run.get('sha256'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vanilla', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--fixed', type=Path)
    args = parser.parse_args()
    results = [check(args.vanilla, 'vanilla'), check(args.baseline, 'baseline')]
    if args.fixed:
        results.append(check(args.fixed, 'fixed'))
    print(json.dumps(results, indent=2))
