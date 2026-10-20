"""Check completed-route phase decisions in a bounded vanilla comparison arena."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'lab/examples/dragon-circling-phase-choice.json'


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
    counts = {}
    for phase in [0, 1, 2, 3]:
        command = f'execute if entity @e[type=minecraft:ender_dragon,tag=choice,nbt={{DragonPhase:{phase}}}]'
        values = []
        for event in captured:
            if event['command'] != command:
                continue
            match = re.fullmatch(r'Test passed\. Count: (\d+)', event['raw'].strip())
            assert match or event['raw'].strip() == 'Test failed', event
            values.append(int(match[1]) if match else 0)
        assert len(values) == 12, values
        counts[phase] = values
    checks['most dragons choose landing at completed routes'] = counts[2][-1] + counts[3][-1] >= 24
    checks['creative observer is never a strafe target'] = not any(counts[1])
    for sample in range(12):
        checks[f'sample {sample} phases account for all dragons'] = sum(counts[p][sample] for p in counts) == 32
    failures = [name for name, passed in checks.items() if not passed]
    if target == 'baseline':
        assert 'most dragons choose landing at completed routes' in failures, counts
        assert all(name in ['most dragons choose landing at completed routes',
                            'creative observer is never a strafe target'] for name in failures), failures
    else:
        assert not failures, (failures, counts)
    assert sum(name.endswith('tick delta') for name in checks) == 14
    return dict(target=target, report=str(report_path), passed=sum(checks.values()), total=len(checks),
                failures=failures, phase_counts=counts,
                ticks=sum(step.get('wait_ticks', 0) for step in scenario['steps']),
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
