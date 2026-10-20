"""Verify captured first-circling movement and initialization controls."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'lab/examples/dragon-initial-circling-route.json'


def check(report_path, target):
    report = json.loads(Path(report_path).read_text())
    assert report['complete'], 'incomplete arena'
    run = report['targets'][target]
    assert run['stopped'], 'scratch server still running'
    row, = run['attempts']
    assert row['sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    scenario = json.loads(FIXTURE.read_text())
    expected = scenario['setup'] + [step['command'] for step in scenario['steps']] + scenario['cleanup']
    events = iter(row['events'])
    captured = [next(event for event in events if event['command'] == command) for command in expected]
    assert captured[-1]['raw'].strip() == 'Test passed', 'boss cleanup failed'
    cold = [event for event in captured if re.search(r'tag=cold_\d+,limit=1\] Pos$', event['command'])]
    assert len(cold) == 32
    heights = []
    for event in cold:
        match = re.search(r'\[([^\[\]]+)\]$', event['raw'].strip())
        assert match, event
        values = [float(v.strip().removesuffix('d')) for v in match[1].split(',')]
        assert len(values) == 3
        heights.append(values[1])
    checks = row['checks']
    failures = [name for name, passed in checks.items() if not passed]
    if target == 'baseline':
        assert any(y > 160 for y in heights), 'baseline did not take an unrelated high route'
        assert all(re.search(r'tag=cold_\d+,limit=1\] Pos$', name) for name in failures), failures
    else:
        assert all(abs(y - 159.99399999976157) < 1e-10 for y in heights), heights
        assert not failures, failures
    assert len([name for name in checks if name.endswith('tick delta')]) == 5
    return dict(target=target, report=str(report_path), passed=sum(checks.values()), total=len(checks),
                failures=failures, cold_heights=heights, ticks=sum(step.get('wait_ticks', 0) for step in scenario['steps']),
                fixture_sha256=row['sha256'], stimulus_sha256=hashlib.sha256(json.dumps(expected).encode()).hexdigest(),
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
