"""Check real Wither-skull item placement and final-wall summoning."""
import json
from pathlib import Path

FIXTURE = Path(__file__).parents[1] / "fixtures/wither-wall-placement/cases.json"


def check_report(report, *, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    expected = {f"{trial}-{case['id']}": case
                for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == list(expected)
    passed = total = 0
    failed, commands, placements = [], {}, {}
    for row in report['rows']:
        case = expected[row['case']]
        checks = dict(row['checks'])
        checks['boss_spawn'] = row['spawned'] == case['spawn']
        checks['placed_variant'] = (row['cleared'] if case['spawn'] else
                                   row['wall'] if case['wall'] else row['floor'])
        checks['skull_block_entity'] = (row['spawn_window'] if case['spawn'] else
                                        'minecraft:skull' in row['block_entity'])
        bosses = [p for p in row['packets'] if p['packet'] == 'ClientboundAddEntityPacket'
                  and 'type=WITHER,' in p['detail']]
        checks['spawn_packet_count'] = len(bosses) == int(case['spawn'])
        placements[row['case']] = dict(wall=row['wall'], floor=row['floor'],
                                       cleared=row['cleared'], spawned=row['spawned'])
        assert row['verified_ticks'] == (54 if row is report['rows'][-1] else 29)
        commands[row['case']] = row['gameplay_sha256']
        for name, value in checks.items():
            total += 1
            passed += bool(value)
            if not value:
                failed.append([row['case'], name])
    if not baseline:
        assert not failed, failed
    return dict(passed=passed, total=total, failed=failed, command_sha256=commands,
                placements=placements)


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        result = check_report(json.loads(Path(filename).read_text()))
        print(filename, result['passed'], '/', result['total'])
