"""Check the isolated Wither retaliation traversal regression capture."""

import json
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == [
        f'{trial}-{case}' for trial in (1, 2)
        for case in ('stone', 'immune', 'griefing-off')
    ]
    failed = []
    total = 0
    for row in report['rows']:
        assert row['verified_ticks'] == 65
        assert len(row['checks']) == 27
        assert [pulse['number'] for pulse in row['pulses']] == [1, 2]
        for pulse in row['pulses']:
            breaking = row['case'].endswith('-stone') and pulse['number'] == 1
            positions = [[x, y, z] for z in (14, 16) for y in (80, 82) for x in (14, 16)] if breaking else []
            expected = sorted(positions) if baseline else positions
            assert pulse['positions'] == expected, (row['case'], pulse['positions'], expected)
            assert len(pulse['destroy_effects']) == len(positions)
            assert len(pulse['break_events']) == int(breaking)
            assert not any(
                packet['packet'] == 'ClientboundLevelEventPacket'
                and ('DESTROY_BLOCK' in packet['detail'] or 'SOUND_WITHER_BLOCK_BREAK' in packet['detail'])
                for packet in pulse['before_packets']
            )
        for name, passed in row['checks'].items():
            expected_failure = baseline and row['case'].endswith('-stone') and name == 'pulse1_vanilla_order'
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (2 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
