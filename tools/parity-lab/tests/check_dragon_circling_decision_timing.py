"""Check the bounded circling arena's captured console command results."""
import argparse
import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'lab/examples/dragon-circling-decision-timing.json'


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
    captured = []
    for command in expected:
        event = next(event for event in events if event['command'] == command)
        captured.append(event)
    assert captured[-1]['raw'].strip() == 'Test passed', 'boss cleanup failed'
    samples = [event for event in captured if 'tag=orbit_timing,nbt={DragonPhase:0}' in event['command']]
    assert len(samples) == 33
    counts = []
    for event in samples:
        raw = event['raw'].strip()
        assert raw == 'Test failed' or raw.startswith('Test passed. Count: '), raw
        count = 0 if raw == 'Test failed' else int(raw.rsplit(': ', 1)[1])
        assert 0 <= count <= 8
        counts.append(count)
    checks = row['checks']
    failures = [name for name, passed in checks.items() if not passed]
    if target == 'baseline':
        assert min(counts) < 8, 'baseline did not reproduce an early phase change'
        assert all('tag=orbit_timing,nbt={DragonPhase:0}' in name for name in failures), failures
    else:
        assert counts == [8] * 33, counts
        assert not failures, failures
    assert len([name for name in checks if name.endswith('tick delta')]) == 34
    return {
        'target': target,
        'report': str(report_path),
        'passed': sum(checks.values()),
        'total': len(checks),
        'failures': failures,
        'circling_counts': counts,
        'ticks': sum(step.get('wait_ticks', 0) for step in scenario['steps']),
        'fixture_sha256': row['sha256'],
        'stimulus_sha256': hashlib.sha256(json.dumps(expected).encode()).hexdigest(),
        'stopped': run['stopped'],
        'binary': run.get('binary'),
        'binary_sha256': run.get('sha256'),
    }


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
