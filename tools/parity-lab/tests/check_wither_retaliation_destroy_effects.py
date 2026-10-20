"""Check Wither retaliation destruction effects from the isolated protocol capture."""

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
        assert len(row['checks']) == 24
        assert [pulse['number'] for pulse in row['pulses']] == [1, 2]
        for pulse in row['pulses']:
            solid = row['case'] in ('stone', 'seagrass') and pulse['number'] == 1
            fluid = row['case'] in ('water', 'lava') or (
                row['case'] == 'seagrass' and pulse['number'] == 2
            )
            effects = pulse['destroy_effects']
            assert len(effects) == int(solid or (fluid and not baseline))
            for packet in effects:
                event = 'PARTICLES_DESTROY_BLOCK' if baseline else 'PARTICLES_AND_SOUND_DESTROY_BLOCK'
                assert 'event=' + event + ',' in packet['detail']
                assert 'position=(14, 81, 14)' in packet['detail']
                assert 'broadcast=false' in packet['detail']
            assert len(pulse['break_events']) == int(solid)
            assert all(
                'position=(15, 80, 15)' in packet['detail']
                and 'broadcast=false' in packet['detail']
                for packet in pulse['break_events']
            )
            assert not any(
                packet['packet'] == 'ClientboundLevelEventPacket'
                and ('DESTROY_BLOCK' in packet['detail'] or 'SOUND_WITHER_BLOCK_BREAK' in packet['detail'])
                for packet in pulse['before_packets']
            )
        for name, passed in row['checks'].items():
            fluid = row['case'] in ('water', 'lava') or (
                row['case'] == 'seagrass' and name.startswith('pulse2_')
            )
            solid = row['case'] in ('stone', 'seagrass') and name.startswith('pulse1_')
            expected_failure = baseline and (
                fluid and name.endswith('_destroy_effect_count')
                or solid and name.endswith('_destroy_effect_properties')
            )
            assert passed != expected_failure, (row['case'], name, passed)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (7 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as source:
        print(json.dumps(check_report(json.load(source), '--baseline' in sys.argv)))
