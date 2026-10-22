"""Check Wither reload immunity and observer state against official 26.3."""
import hashlib
import json
from pathlib import Path
import re
import sys


def number(raw):
    values = re.findall(r'entity data: (-?[\d.]+)f?\s*$', raw)
    assert len(values) == 1, raw
    return float(values[0])


def vector(raw):
    values = re.findall(r'entity data: \[(-?[\d.]+)d,\s*(-?[\d.]+)d,\s*(-?[\d.]+)d\]', raw)
    assert len(values) == 1, raw
    return list(map(float, values[0]))


def invul_values(packets, entity_id):
    return [int(value) for packet in packets
            if packet['packet'] == 'ClientboundSetEntityDataPacket'
            and re.search(r'entityId=' + str(entity_id) + r'\b', packet['detail'])
            for value in re.findall(r'EntityMetadata\(id=19, type=[^,]+, value=(-?\d+)\)',
                                    packet['detail'])]


def check_report(report, baseline=False):
    fixture = Path(__file__).parents[1] / 'fixtures/wither-invul-reload/cases.json'
    spec = json.loads(fixture.read_text())
    assert report['fixture_sha256'] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [e['command'] for e in report['setup']] == spec['setup']
    cases = {f"{trial}-{case['id']}": case
             for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert len(report['rows']) == len(cases)
    assert [row['case'] for row in report['rows']] == list(cases)
    required = {'arena_clear', 'single_boss', 'no_ai', 'player_creative', 'no_environment_error', 'client_alive'}
    total, failed = 0, []
    entity_ids = set()
    for index, row in enumerate(report['rows']):
        case = cases[row['case']]
        assert row['operation_command'] == (
            f"data {case['operation']} entity @e[tag=pp_boss,limit=1] {case['payload']}")
        assert row['verified_ticks'] == 46 + 2 * spec['settle_ticks'] + (
            26 if index == len(report['rows']) - 1 else 0)
        assert set(row['checks']) == required
        spawns = [p['detail'] for p in row['spawn_packets']
                  if p['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER,' in p['detail']]
        assert len(spawns) == 1, (row['case'], spawns)
        entity_id = int(re.search(r'entityId=(\d+)', spawns[0])[1])
        assert entity_id not in entity_ids
        entity_ids.add(entity_id)
        initial_values = invul_values(row['spawn_packets'], entity_id)
        updates = invul_values(row['update_packets'], entity_id)
        cached_initial = initial_values[-1] if initial_values else 0
        cached_final = updates[-1] if updates else cached_initial
        before_health = 300.0 if case['initial'] else 293.0
        final_health = before_health - (7.0 if case['expected'] == 0 else 0.0)
        checks = dict(row['checks'])
        checks.update(
            initial_server_timer=number(row['initial_invul']) == case['initial'],
            initial_client_timer=cached_initial == case['initial'],
            initial_full_health=number(row['initial_health']) == 300.0,
            initial_damage_gate=('Applied' in row['initial_damage']) == (case['initial'] == 0),
            initial_damage_health=number(row['before_health']) == before_health,
            final_server_timer=number(row['final_invul']) == case['expected'],
            final_metadata_delta=updates == case['metadata'],
            final_client_timer=cached_final == case['expected'],
            final_damage_gate=('Applied' in row['damage_result']) == (case['expected'] == 0),
            final_damage_health=number(row['final_health']) == final_health,
            initial_spawn_position='x=15.5, y=85.0, z=15.5,' in spawns[0],
            final_position=vector(row['final_pos']) == [15.5, 85.0, 15.5])
        for name, passed in checks.items():
            expected_failure = (baseline and case['id'] == 'remove-active-invul'
                                and name in {'final_server_timer', 'final_metadata_delta',
                                             'final_client_timer', 'final_damage_gate',
                                             'final_damage_health'})
            assert passed != expected_failure, (row['case'], name, passed, updates)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (10 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()),
                                  '--baseline' in sys.argv)))
