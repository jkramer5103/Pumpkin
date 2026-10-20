"""Check Wither route continuation when its invulnerability goal interrupts ranged AI."""

import json
import math
import re
import sys


def inspect_row(row):
    case = row['case'].split('-', 1)[1]
    positions = row['positions']
    assert len(positions) == (3 if case == 'active' else 7)
    assert all(len(pos) == 3 and all(math.isfinite(v) for v in pos) for pos in positions)
    start = positions[0]
    distance = max(math.hypot(pos[0] - start[0], pos[2] - start[2]) for pos in positions[1:])
    row['horizontal_route_distance'] = distance
    if case == 'interrupted':
        row['checks']['interrupted_route_continues'] = distance > 1.0
    elif case == 'active':
        row['checks']['visible_target_stops_route'] = distance < 1.0
    else:
        row['checks']['initial_spawn_stays_still'] = distance < 0.001

    def entity_id(kind):
        additions = [p['detail'] for p in row['packets']
                     if p['packet'] == 'ClientboundAddEntityPacket' and f'type={kind},' in p['detail']]
        return int(re.search(r'entityId=(\d+)', additions[0])[1]) if len(additions) == 1 else None

    boss, target = entity_id('WITHER'), entity_id('SHEEP')
    row['checks']['boss_and_target_seen'] = boss is not None and target is not None
    values = [int(v) for p in row['packets']
              if p['packet'] == 'ClientboundSetEntityDataPacket'
              and re.search(r'entityId=' + str(boss) + r'\b', p['detail'])
              for v in re.findall(r'EntityMetadata\(id=16, type=[^,]+, value=(\d+)\)', p['detail'])]
    row['main_target_values'] = values
    row['checks']['main_target_control'] = not any(values) if case == 'spawn' else target in values
    timers = [event for event in row['events']
              if event['command'] == 'data get entity @e[tag=pp_boss,limit=1] Invul']
    assert len(timers) == 1
    final = timers[0]
    expected = {'interrupted': 176, 'active': 0, 'spawn': 174}[case]
    row['checks']['invulnerability_countdown'] = bool(re.search(r'(?<!\d)' + str(expected) + r'(?!\d)', final['raw']))
    return row


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == [
        f'{trial}-{case}' for trial in (1, 2) for case in ('interrupted', 'active', 'spawn')
    ]
    total = 0
    failed = []
    for row in report['rows']:
        assert row['verified_ticks'] == (35 if row['case'].endswith('active') else 51)
        inspect_row(row)
        for name, passed in row['checks'].items():
            expected_failure = baseline and name == 'interrupted_route_continues'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (2 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
