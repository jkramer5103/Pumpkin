"""Check that the first fight scan does not duplicate overlapping crystals."""
import hashlib
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
    fixture = pathlib.Path(__file__).resolve().parents[1] / 'fixtures/dragon-initial-crystal-membership/cases.json'
    cases = json.loads(fixture.read_text())['cases']
    assert report['complete'] and report['target'] == target
    assert report['stopped'] and report['client_alive'] and report['cleanup_passed']
    assert report['fixture']['sha256'] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert len(report['rows']) == len(cases)
    samples = []
    for row, (name, x, z, ox, oz) in zip(report['rows'], cases, strict=True):
        assert row['name'] == name and row['x'] == x and row['z'] == z
        assert row['player_present'] and 'Test passed' in row['present_before']
        assert 'Test passed' in row['present_after']
        assert row['radius'] == 2 + ((row['height'] - 76) // 3) // 3
        offset = lambda side: row['radius'] + .5 if side == 'max' else -row['radius'] - .5 if side == 'min' else .5
        expected = [x + offset(ox), 120., z + offset(oz)]
        assert vector(row['pos_before']) == vector(row['pos_after']) == row['pos'] == expected
        assert re.fullmatch(r'Test passed|Test failed(?:\. Count: [1-9]\d*)?', row['no_duplicate'])
        samples.append({'name': name, 'no_duplicate': row['no_duplicate'] == 'Test passed'})
    return {'samples': samples, 'passed': sum(sample['no_duplicate'] for sample in samples), 'total': len(samples)}


if __name__ == '__main__':
    result = check(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    assert result['passed'] == (2 if sys.argv[2] == 'baseline' else result['total'])
