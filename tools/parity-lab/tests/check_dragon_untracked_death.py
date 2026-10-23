"""Check fight completion after tracked and unrelated Ender Dragon deaths."""
import json
import pathlib
import sys


def check(path):
    report = json.loads(pathlib.Path(path).read_text())
    fixture = pathlib.Path(__file__).resolve().parents[1] / 'fixtures/dragon-untracked-death/cases.json'
    cases = json.loads(fixture.read_text())['trials']
    assert report['complete'] and report['stopped'] and report['arena_ready']
    assert report['initial_dragon_present'] and report['client_alive'] and report['player_present']
    assert report['cleanup_passed'] and 'Test passed' in report['no_dragon']
    assert len(report['trials']) == len(cases)
    failures = []
    for row, case in zip(report['trials'], cases, strict=True):
        assert row['name'] == case['name'] and 'Killed' in row['kill']
        assert 'Test passed' in row['extra_removed'], row
        for key, expected in [('marker', case['marker_preserved']),
                              ('portal', case['portal_active']),
                              ('tracked_present', case['tracked_alive'])]:
            if ('Test passed' in row[key]) != expected:
                failures.append(f"{case['name']}: {key}")
    if 'Test passed' not in report['final_marker']:
        failures.append('final marker')
    assert not failures, failures
    return {'trials': len(cases), 'tracked_death_control': True,
            'unrelated_deaths_preserve_portal': True, 'headless_only': True}


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1]), indent=2))
