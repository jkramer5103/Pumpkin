"""Check the isolated Wither construction rotation arena reports."""
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).parents[1] / "fixtures/wither-construction-rotation/cases.json"


def check_report(report, *, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    expected = {f"{trial}-{case['id']}": case
                for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == list(expected)
    passed = total = 0
    failed, commands, effects = [], {}, {}
    for row in report['rows']:
        case = expected[row['case']]
        checks = {k: v for k, v in row['checks'].items() if k != 'spawn_window'}
        checks['boss_spawned'] = row['spawned'] == case['spawn']
        checks['skull_placement'] = row['skull_placed'] == (case['skull_placed'] and not case['spawn'])
        checks['inventory_consumed'] = row['inventory_consumed'] == case['skull_placed']
        remaining = [] if case['spawn'] else [p for i, p in enumerate(case['arms'] + [case['base']])
                                             if not (case.get('incomplete_base') and i == 1)]
        checks['construction_blocks'] = row['remaining_blocks'] == remaining
        spawns = [p['detail'] for p in row['packets'] if p['packet'] == 'ClientboundAddEntityPacket'
                  and 'type=WITHER,' in p['detail']]
        checks['spawn_packet_count'] = len(spawns) == int(case['spawn'])
        if case['spawn']:
            checks['spawn_window'] = row.get('spawn_window', row['checks'].get('spawn_window')) is True
            match = re.search(r'x=([^,]+), y=([^,]+), z=([^,]+),.*yaw=([^,]+),', spawns[0]) if spawns else None
            pose = [float(x) for x in match.groups()] if match else []
            checks['spawn_position_rotation'] = pose == [case['base'][0] + .5, case['base'][1] + .55,
                                                         case['base'][2] + .5, case['yaw']]
        destruction = []
        for packet in row['packets']:
            if packet['packet'] != 'ClientboundLevelEventPacket' or 'event=PARTICLES_AND_SOUND_DESTROY_BLOCK,' not in packet['detail']:
                continue
            match = re.search(r'position=\((-?\d+), (-?\d+), (-?\d+)\).*stateId=(\d+)', packet['detail'])
            assert match, packet
            destruction.append([int(x) for x in match.groups()])
        effects[row['case']] = destruction
        cells = [p[:3] for p in destruction]
        checks['construction_effect_cells'] = (len(cells) == 9 and len({tuple(p) for p in cells}) == 9
                                               and all(p in cells for p in case['skulls'] + case['arms'] + [case['base'], case['gap']])) if case['spawn'] else not cells
        assert row['verified_ticks'] == 31
        commands[row['case']] = row['gameplay_sha256']
        for name, value in checks.items():
            total += 1
            passed += bool(value)
            if not value:
                failed.append([row['case'], name])
    if not baseline:
        assert not failed, failed
    return dict(passed=passed, total=total, failed=failed, command_sha256=commands,
                destruction_sequences=effects)


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        result = check_report(json.loads(Path(filename).read_text()))
        print(filename, result['passed'], '/', result['total'])
