"""Check crystal hitbox membership through actual dragon takeoff steering."""
import json
import pathlib
import re
import sys


def vector(raw):
    match = re.search(r'\[([^\[\]]+)\]', raw)
    assert match, raw
    return [float(value.strip().removesuffix('d')) for value in match[1].split(',')]


def check(path, target):
    report = json.loads(pathlib.Path(path).read_text())
    fixture = pathlib.Path(__file__).resolve().parents[1] / 'fixtures/dragon-crystal-count-hitboxes/cases.json'
    cases = json.loads(fixture.read_text())['cases']
    assert report['complete'] and report['target'] == target
    assert report['stopped'] and report['client_alive'] and report['cleanup_passed']
    assert report['initial_dragon_present'] and len(report['rows']) == len(cases)
    assert report['dragon_persistent'].endswith('1b')
    assert '[' in report['dragon_uuid']
    spike = report['spike']
    assert spike['x'] == 42 and spike['z'] == 0
    assert spike['radius'] == 2 + ((spike['height'] - 76) // 3) // 3
    edge_positions = {
        f'{side}_{axis}{offset}': spike[axis] + sign * spike['radius'] + delta
        for side, sign in [('min', -1), ('max', 1)]
        for axis in ['x', 'z']
        for offset, delta in [('-1', -1.), ('-.5', -.5), ('+.5', .5), ('+1', 1.)]
    }
    checks = []
    for row, case in zip(report['rows'], cases, strict=True):
        assert row['name'] == case['name'] and row['player_present']
        assert row['dragon_uuid'] == report['dragon_uuid']
        before, after = vector(row['before']), vector(row['after'])
        motion = vector(row['motion'])
        assert before == [40., 120., 0.], before
        assert row['phase_before'].endswith('4') and row['phase_after'].endswith('4')
        clock = lambda value: int(re.search(r'\d+', value)[0])
        assert clock(row['clock_after']) - clock(row['clock_before']) == 101
        if row['crystal_pos'] is not None:
            expected_pos = [
                edge_positions[value] if isinstance(value, str)
                else value + (spike['x'] if index == 0 else spike['z'] if index == 2 else 0)
                for index, value in enumerate(case['position'])
            ]
            assert row['crystal_pos'] == expected_pos
            assert 'Test passed' in row['crystal_present']
            assert vector(row['crystal_pos_observed']) == row['crystal_pos']
        else:
            assert case['position'] is None
        counted = after[1] < before[1]
        assert abs(abs(after[1]-before[1]) - 0.006000000238418579) < 1e-10
        assert (motion[1] < 0) == counted
        checks.append({'name':case['name'],'counted':counted,'expected':case['counted'],'matches_vanilla':counted == case['counted'],'y':after[1]})
    assert not any(any(token in e['raw'] for token in ('Unknown command','Incorrect argument','not loaded','Unknown or incomplete')) for e in report['events'])
    return {'samples':checks,'vanilla_mismatches':sum(not c['matches_vanilla'] for c in checks),'controls_passed':True}


if __name__ == '__main__':
    result = check(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    assert result['vanilla_mismatches'] == (4 if sys.argv[2] == 'baseline' else 0)
