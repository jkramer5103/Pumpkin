"""Check packet-visible Wither retaliation success against a vanilla capture."""

import json
import sys


def check_report(report, baseline=False):
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [row['case'] for row in report['rows']] == [
        'water', 'lava', 'air', 'immune', 'stone', 'seagrass',
    ]
    failed = []
    total = 0
    for row in report['rows']:
        assert row['verified_ticks'] == 65
        assert len(row['checks']) == 18
        assert [pulse['number'] for pulse in row['pulses']] == [1, 2]
        for pulse in row['pulses']:
            assert not any(
                packet['packet'] == 'ClientboundLevelEventPacket'
                and 'SOUND_WITHER_BLOCK_BREAK' in packet['detail']
                for packet in pulse['before_packets']
            )
            expected = int(row['case'] in ('stone', 'seagrass') and pulse['number'] == 1)
            if baseline and (row['case'] in ('water', 'lava') or (
                row['case'] == 'seagrass' and pulse['number'] == 2
            )):
                expected = 1
            assert len(pulse['break_events']) == expected
            assert all(
                'position=(15, 80, 15)' in packet['detail']
                and 'broadcast=false' in packet['detail']
                for packet in pulse['break_events']
            )
        for name, passed in row['checks'].items():
            expected_failure = baseline and (
                row['case'] in ('water', 'lava')
                and name in ('pulse1_break_event_count', 'pulse2_break_event_count')
                or row['case'] == 'seagrass' and name == 'pulse2_break_event_count'
            )
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (5 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
