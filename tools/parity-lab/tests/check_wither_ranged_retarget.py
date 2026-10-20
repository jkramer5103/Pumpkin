"""Check Wither retaliation metadata and the central skull's attack direction."""

import json
import math
import re
import sys


def inspect_row(row):
    additions = [p['detail'] for p in row['packets'] if p['packet'] == 'ClientboundAddEntityPacket']

    def entities(kind):
        return [s for s in additions if f'type={kind},' in s]

    def entity_id(kind):
        found = entities(kind)
        return int(re.search(r'entityId=(\d+)', found[0])[1]) if len(found) == 1 else None

    boss, old, new = (entity_id(kind) for kind in ('WITHER', 'SHEEP', 'COW'))
    row['checks']['entities_seen'] = all(value is not None for value in (boss, old, new))
    values = [int(v) for p in row['packets']
              if p['packet'] == 'ClientboundSetEntityDataPacket'
              and re.search(r'entityId=' + str(boss) + r'\b', p['detail'])
              for v in re.findall(r'EntityMetadata\(id=16, type=[^,]+, value=(\d+)\)', p['detail'])]
    switch = row['case'] != 'unchanged'
    row['main_target_values'] = values
    row['checks']['initial_main_target'] = old is not None and old in values
    row['checks']['final_main_target'] = bool(values) and values[-1] == (new if switch else old)
    central = []
    for shot in entities('WITHER_SKULL'):
        y = float(re.search(r', y=([^,]+)', shot)[1])
        if abs(y - 83.0) < 0.001:
            movement = [float(v) for v in re.search(r'movement=\(([^)]+)\)', shot)[1].split(',')]
            central.append(movement)
    row['central_skull_movements'] = central
    row['checks']['one_central_skull'] = len(central) == 1 and all(math.isfinite(v) for v in central[0])
    expected_positive = 'left-right' in row['case']
    row['checks']['central_skull_retargets'] = (
        len(central) == 1 and central[0][0] * (1 if expected_positive else -1) > 0.01
    )
    return row


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == [
        '1-left-right', '1-right-left', '2-left-right', '2-right-left', 'unchanged'
    ]
    total = 0
    failed = []
    for row in report['rows']:
        assert row['verified_ticks'] == 68
        inspect_row(row)
        for name, passed in row['checks'].items():
            expected_failure = baseline and row['case'] != 'unchanged' and name == 'central_skull_retargets'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (4 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
