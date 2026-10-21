"""Check the isolated dragon block-breaking packet fixture against raw reports."""
import argparse
import hashlib
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/dragon-block-break-event/cases.json'


def check(path, target):
    report = json.loads(Path(path).read_text())
    fixture = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['target'] == target and report['shared_engine_lock']
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    expected = [(trial, case) for trial in range(1, fixture['trials'] + 1)
                for case in fixture['cases']]
    assert len(report['rows']) == len(expected)
    failures = []
    stimuli = {}
    ticks = 0
    observations = {}
    for row, (trial, case) in zip(report['rows'], expected):
        key = f"{trial}-{case['id']}"
        assert row['case'] == key and row['spec'] == case
        assert all(row['checks'].values()), (key, row['checks'])
        assert row['verified_ticks'] == 23
        ticks += row['verified_ticks']
        stimuli[key] = hashlib.sha256(json.dumps([
            event['command'] for event in row['events']
            if event['command'] != 'time query gametime'
        ]).encode()).hexdigest()
        assert stimuli[key] == row['gameplay_sha256']
        effects = [p['detail'] for p in row['packets']
                   if p['packet'] == 'ClientboundLevelEventPacket']
        assert effects == [p['detail'] for p in row['effects']]
        assert all('event=PARTICLES_DRAGON_BLOCK_BREAK,' in e for e in effects), (key, effects)
        assert all('broadcast=false)' in e and e.endswith(' stateId=0') for e in effects)
        positions = [tuple(map(int, re.search(r'position=\((-?\d+), (-?\d+), (-?\d+)\)', e).groups()))
                     for e in effects]
        # Check conservative head/body regions; exact multipart dimensions are a separate issue.
        body = lambda p: 12 <= p[0] <= 20 and 99 <= p[1] <= 104 and 12 <= p[2] <= 20
        head = lambda p: 14 <= p[0] <= 17 and 99 <= p[1] <= 102 and 8 <= p[2] <= 12
        if len(positions) != case['count']:
            failures.append(key)
        elif case['count'] == 1:
            assert body(positions[0]), (key, positions)
        elif case['count'] == 2:
            assert head(positions[0]) and body(positions[1]), (key, positions)
        observations[key] = positions
    expected_failures = [f'{trial}-{case}' for trial in range(1, fixture['trials'] + 1)
                         for case in ('body-stone', 'head-and-body')]
    assert failures == (expected_failures if target == 'baseline' else []), failures
    return {'passed': len(expected) - len(failures), 'total': len(expected),
            'failures': failures, 'positions': observations, 'controlled_ticks': ticks,
            'stimulus_sha256': stimuli, 'binary_sha256': report.get('binary_sha256'),
            'directory': report['directory']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('vanilla', 'baseline', 'fixed'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    results = {name: check(getattr(args, name), name) for name in ('vanilla', 'baseline', 'fixed')}
    assert len({json.dumps(r['stimulus_sha256'], sort_keys=True) for r in results.values()}) == 1
    print(json.dumps(results, indent=2))
