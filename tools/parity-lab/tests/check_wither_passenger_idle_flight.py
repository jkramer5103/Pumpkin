"""Check Wither strolls with passengers against a controlled world report."""

import json
import math
import re
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    cases = ('player', 'armor_stand', 'zombie', 'empty')
    assert [row['case'] for row in report['rows']] == [
        f'{trial}-{case}' for trial in (1, 2) for case in cases]
    failed, total = [], 0
    for row in report['rows']:
        case = row['case'].split('-', 1)[1]
        positions = row['positions']
        assert 2 <= len(positions) <= 121
        assert all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in positions)
        observation_ticks = (len(positions) - 1) * 10
        if case == 'zombie':
            assert observation_ticks == 120
        else:
            assert 10 <= observation_ticks <= 1200
        assert row['verified_ticks'] == observation_ticks + 25 + (26 if row['case'] == '2-empty' else 0)
        distance = max(math.hypot(p[0] - positions[0][0], p[2] - positions[0][2])
                       for p in positions)
        assert abs(distance - row['distance']) < 1e-9
        if case != 'zombie' and distance <= 1:
            assert observation_ticks == 1200, 'Flight observation ended prematurely'
        row['checks']['controlling_rider_suppresses_flight' if case == 'zombie' else 'idle_flight'] = (
            distance < 0.001 if case == 'zombie' else distance > 1)
        bosses = [p['detail'] for p in row['packets']
                  if p['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER,' in p['detail']]
        boss_ids = {re.search(r'entityId=(\d+)', boss)[1] for boss in bosses}
        row['checks']['one_boss_tracked'] = len(boss_ids) == 1
        boss = next(iter(boss_ids)) if len(boss_ids) == 1 else 'missing'
        values = [int(value) for packet in row['packets']
                  if packet['packet'] == 'ClientboundSetEntityDataPacket'
                  and re.search(r'entityId=' + boss + r'\b', packet['detail'])
                  for value in re.findall(r'EntityMetadata\(id=16, type=[^,]+, value=(\d+)\)', packet['detail'])]
        row['checks']['main_head_has_no_target'] = not any(values)
        for name, passed in row['checks'].items():
            expected_failure = baseline and case in ('player', 'armor_stand') and name == 'idle_flight'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
