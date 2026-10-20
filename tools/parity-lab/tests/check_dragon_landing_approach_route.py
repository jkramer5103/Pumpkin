"""Check bounded landing approach progression against vanilla server observations."""
import argparse
import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'lab/examples/dragon-landing-approach-route.json'


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
    presence = next(event for event in captured if event['command'] == 'execute if entity @e[type=minecraft:ender_dragon]')
    checks['all four dragons present'] = presence['raw'].strip() == 'Test passed. Count: 4'
    failures = [name for name, passed in checks.items() if not passed]
    descent_failures = [name for name in checks if name.endswith('nbt={DragonPhase:3}]')]
    assert len(descent_failures) == 3
    if target == 'baseline':
        assert set(failures) == set(descent_failures), failures
    else:
        assert not failures, failures
    return dict(target=target, report=str(report_path), passed=sum(checks.values()), total=len(checks),
                failures=failures, ticks=sum(step.get('wait_ticks', 0) for step in scenario['steps']),
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
