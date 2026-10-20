"""Check failed and partial dragon flight routes against vanilla server observations."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'lab/examples/dragon-unreachable-flight-path.json'


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
    # Compare NBT numbers: Pumpkin prints exact integers as 40d, vanilla as 40.0d.
    for index, event in enumerate(captured[len(scenario['setup']):][:len(scenario['steps'])]):
        command = event['command']
        if not command.startswith('data get entity') or not any(
            'tag=' + tag + ',' in command for tag in ('stalled', 'stalled_two')
        ):
            continue
        match = re.search(r'\[([^\[\]]+)\]\s*$', event['raw'])
        assert match, event
        values = [float(value.strip().removesuffix('d')) for value in match[1].split(',')]
        assert len(values) == 3, event
        if command.endswith(' Pos'):
            height = 120.0 if 'tag=stalled_two,' in command else 90.0
            checks[str(index) + ' no movement'] = values == [40.0, height, 0.0]
        elif command.endswith(' Motion'):
            checks[str(index) + ' zero velocity'] = values == [0.0, 0.0, 0.0]
    presence = next(event for event in captured if event['command'] == 'execute if entity @e[type=minecraft:ender_dragon]')
    checks['all five dragons present'] = presence['raw'].strip() == 'Test passed. Count: 5'
    failures = [name for name, passed in checks.items() if not passed]
    movement_failures = [name for name in checks if name.endswith(('no movement', 'zero velocity'))]
    partial_queries = [name for name in checks if 'tag=partial,nbt={DragonPhase:2}' in name]
    assert len(movement_failures) == 4 and len(partial_queries) == 2
    expected_failures = movement_failures + partial_queries[1:]
    if target == 'baseline':
        assert set(failures) == set(expected_failures), failures
    else:
        assert not failures, failures
    return dict(target=target, report=str(report_path), passed=sum(checks.values()), total=len(checks),
                failures=failures, ticks=sum(step.get('wait_ticks', 0) for step in scenario['steps']),
                fixture_sha256=row['sha256'], stimulus_sha256=hashlib.sha256(json.dumps(commands).encode()).hexdigest(),
                stopped=run['stopped'], movement_recomputed_from_raw_nbt=True, binary=run.get('binary'), binary_sha256=run.get('sha256'))


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
