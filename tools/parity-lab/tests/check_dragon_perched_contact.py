"""Check perched wing contact using raw observations from isolated server runs."""
import argparse
import hashlib
import json
import re
from pathlib import Path

CASES = Path(__file__).resolve().parents[1] / 'fixtures/dragon-perched-contact/cases.json'
MAX_STARTING_HORIZONTAL_MOTION = 0.001
MIN_PUSH_DELTA = 0.01


def number(raw):
    return float(raw.split(': ', 1)[-1].strip().rstrip('fbds'))


def vector(raw):
    match = re.search(r'\[([^\[\]]+)\]\s*$', raw)
    assert match, raw
    values = [float(value.strip().removesuffix('d')) for value in match[1].split(',')]
    assert len(values) == 3, raw
    return values


def check(path, target):
    report = json.loads(Path(path).read_text())
    assert report['complete'], 'incomplete run'
    assert report['fixture_sha256'] == hashlib.sha256(CASES.read_bytes()).hexdigest()
    run = report['targets'][target]
    assert run['stopped'], 'scratch server still running'
    fixture = json.loads(CASES.read_text())
    cases = [(trial, case) for trial in range(1, fixture['trials'] + 1) for case in fixture['cases']]
    assert len(run['attempts']) == len(cases)
    failures = []
    stimuli = []
    for row, (trial, case) in zip(run['attempts'], cases):
        label = f"{trial} {case['id']}"
        assert (row['trial'], row['case'], row['phase'], row['mode'], row['noai']) == (
            trial, case['id'], case['phase'], case['mode'], case['no_ai']
        ), label
        assert vector(row['player_before_Pos']) == fixture['player_position'], label
        assert vector(row['dragon_before_Pos']) == fixture['dragon_position'], label
        assert number(row['player_before_Health']) == 20.0, label
        assert number(row['dragon_before_HurtTime']) == 0, label
        assert number(row['dragon_before_DragonPhase']) == case['phase'], label
        assert number(row['dragon_after_phase']) == case['phase'], label
        assert number(row['player_after_Health']) == case['health_after'], label
        assert row['clear_before'].strip() == 'Test passed', label
        assert all(ok for key, ok in row['checks'].items() if key != 'push'), label
        before, after = vector(row['player_before_Motion']), vector(row['player_after_Motion'])
        # Pumpkin retains a small horizontal velocity after teleporting. Bound it
        # below the detection threshold and check the change during contact.
        assert max(abs(before[0]), abs(before[2])) < MAX_STARTING_HORIZONTAL_MOTION, label
        delta_x = after[0] - before[0]
        pushed = delta_x > MIN_PUSH_DELTA
        if not case['push']:
            assert abs(delta_x) < MAX_STARTING_HORIZONTAL_MOTION, label
        if pushed != case['push']:
            failures.append(label)
        # Exclude clock polls, which can vary in count between console and RCON.
        stimuli.append([event['command'] for event in row['events'] if event['command'] != 'time query gametime'])
    expected = [f'{trial} perched_{mode}' for trial in range(1, fixture['trials'] + 1)
                for mode in ('survival', 'adventure', 'breathing')] if target == 'baseline' else []
    assert failures == expected, failures
    return dict(target=target, contact_cases=len(cases), push_failures=failures,
                fixture_sha256=hashlib.sha256(CASES.read_bytes()).hexdigest(),
                stimulus_sha256=hashlib.sha256(json.dumps(stimuli).encode()).hexdigest(),
                binary=run.get('binary'), binary_sha256=run.get('sha256'), stopped=run['stopped'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vanilla', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--fixed', type=Path)
    args = parser.parse_args()
    results = [check(args.vanilla, 'vanilla'), check(args.baseline, 'baseline')]
    if args.fixed:
        results.append(check(args.fixed, 'fixed'))
    assert len({row['stimulus_sha256'] for row in results}) == 1, 'different stimuli'
    print(json.dumps(results, indent=2))
