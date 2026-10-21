"""Check pristine nether-star spawn positions from real Wither deaths."""
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).parents[1] / "fixtures/wither-star-position/cases.json"


def check_report(report, *, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    expected = [(trial, case) for trial in range(1, spec['trials'] + 1)
                for case in spec['cases']]
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert len(report['rows']) == len(expected)
    passed = total = 0
    failed, commands, positions = [], {}, {}
    for index, (row, (trial, case)) in enumerate(zip(report['rows'], expected)):
        key = f"{trial}-{case['id']}"
        assert (row['trial'], row['case']) == (trial, case['id'])
        assert row['verified_ticks'] == (52 if index == len(expected) - 1 else 27)
        assert row['pos'] == case['pos'] and row['lethal'] == case['lethal']
        checks = dict(row['checks'])
        if case['lethal']:
            raw = row['initial_item']
            assert 'Age: -6000s' in raw and 'PickupDelay: 10s' in raw
            assert 'OnGround: 0b' in raw
            position = [float(value.rstrip('d')) for value in
                        re.search(r'Pos: \[([^]]+)\]', raw)[1].split(', ')]
            positions[key] = position
            checks['star_position'] = position == case['pos']
        else:
            checks['no_drop'] = all('No entity was found' in row[name] for name in
                                    ('immediate_item', 'first_tick_item', 'item_nbt'))
        commands[key] = row['gameplay_sha256']
        for name, value in checks.items():
            total += 1
            passed += bool(value)
            if not value:
                failed.append([key, name])
    if not baseline:
        assert not failed, failed
    return dict(passed=passed, total=total, failed=failed,
                command_sha256=commands, positions=positions)


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        result = check_report(json.loads(Path(filename).read_text()))
        print(filename, result['passed'], '/', result['total'])
