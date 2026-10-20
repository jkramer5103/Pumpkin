"""Check navigation cancellation after interrupting a running idle Wither stroll."""

import json
import math
import re
import sys


def inspect_row(row):
    case = row['case'].split('-', 1)[1]
    positions = row['positions']
    assert len(positions) == 9
    assert all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in positions)
    tail = positions[-4:]
    row['tail_path_length'] = sum(math.hypot(b[0] - a[0], b[2] - a[2])
                                  for a, b in zip(tail, tail[1:]))
    row['distance'] = max(math.hypot(p[0] - positions[0][0], p[2] - positions[0][2])
                          for p in positions)
    if case == 'spawn':
        row['checks']['spawn_has_no_horizontal_route'] = row['distance'] < 0.001
    else:
        assert 2 <= row['route_detection_ticks'] <= 1200
        before, after = row['preparation'][-2:]
        row['checks']['stroll_was_running'] = math.hypot(after[0] - before[0], after[2] - before[2]) > 0.02
        if case == 'interrupted':
            row['checks']['interrupted_stroll_settles'] = row['tail_path_length'] < 0.1
        else:
            row['checks']['active_flight_control'] = row['distance'] > 0.5

    bosses = [p['detail'] for p in row['packets']
              if p['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER,' in p['detail']]
    boss_ids = {re.search(r'entityId=(\d+)', boss)[1] for boss in bosses}
    row['checks']['one_boss_tracked'] = len(boss_ids) == 1
    boss = next(iter(boss_ids)) if len(boss_ids) == 1 else 'missing'
    values = [int(v) for p in row['packets']
              if p['packet'] == 'ClientboundSetEntityDataPacket'
              and re.search(r'entityId=' + boss + r'\b', p['detail'])
              for v in re.findall(r'EntityMetadata\(id=16, type=[^,]+, value=(\d+)\)', p['detail'])]
    row['checks']['main_head_has_no_target'] = not any(values)
    timer = 0 if case == 'active' else 168
    row['checks']['invulnerability_countdown'] = bool(re.search(r'(?<!\d)' + str(timer) + r'(?!\d)', row['final_invul']))
    return row


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [r['case'] for r in report['rows']] == [
        f'{trial}-{case}' for trial in (1, 2) for case in ('interrupted', 'active', 'spawn')]
    failed, total = [], 0
    for row in report['rows']:
        inspect_row(row)
        assert row['verified_ticks'] == 57 + row.get('route_detection_ticks', 0) + (26 if row['case'] == '2-spawn' else 0)
        for name, passed in row['checks'].items():
            assert passed != (baseline and name == 'interrupted_stroll_settles'), (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
