"""Check live skull NBT reloads against official 26.3 observer metadata."""
import hashlib
import json
from pathlib import Path
import re
import sys


def flag(raw):
    values = re.findall(r'entity data: ([01])b\s*$', raw)
    assert len(values) == 1, raw
    return values[0] == '1'


def vector(raw):
    values = re.findall(r'entity data: \[(-?[\d.]+)d,\s*(-?[\d.]+)d,\s*(-?[\d.]+)d\]', raw)
    assert len(values) == 1, raw
    return list(map(float, values[0]))


def dangerous_values(packets, entity_id):
    return [value == 'true' for packet in packets
            if packet['packet'] == 'ClientboundSetEntityDataPacket'
            and re.search(r'entityId=' + str(entity_id) + r'\b', packet['detail'])
            for value in re.findall(r'EntityMetadata\(id=8, type=[^,]+, value=(true|false)\)',
                                    packet['detail'])]


def check_report(report, baseline=False):
    fixture = Path(__file__).parents[1] / 'fixtures/wither-skull-dangerous-sync/cases.json'
    spec = json.loads(fixture.read_text())
    assert report['fixture_sha256'] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert [e['command'] for e in report['setup']] == spec['setup']
    cases = {f"{trial}-{case['id']}": case
             for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    assert len(report['rows']) == len(cases)
    assert {row['case'] for row in report['rows']} == cases.keys()
    required = {'single_skull', 'player_creative', 'no_environment_error', 'client_alive'}
    total, failed = 0, []
    entity_ids = set()
    for index, row in enumerate(report['rows']):
        case = cases[row['case']]
        assert row['operation_command'] == (
            f"data {case['operation']} entity @e[tag=pp_skull,limit=1] {case['payload']}")
        assert row['verified_ticks'] == 1 + 2 * spec['settle_ticks'] + (
            1 if index == len(report['rows']) - 1 else 0)
        assert set(row['checks']) == required
        spawns = [p['detail'] for p in row['spawn_packets']
                  if p['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER_SKULL,' in p['detail']]
        assert len(spawns) == 1, (row['case'], spawns)
        entity_id = int(re.search(r'entityId=(\d+)', spawns[0])[1])
        assert entity_id not in entity_ids
        entity_ids.add(entity_id)
        initial_values = dangerous_values(row['spawn_packets'], entity_id)
        updates = dangerous_values(row['update_packets'], entity_id)
        cached_initial = initial_values[-1] if initial_values else False
        cached_final = updates[-1] if updates else cached_initial
        checks = dict(row['checks'])
        checks.update(
            initial_server_flag=flag(row['initial_nbt']) == case['initial'],
            initial_client_flag=cached_initial == case['initial'],
            initial_spawn_position='x=15.5, y=85.0, z=15.5,' in spawns[0],
            final_server_flag=flag(row['final_nbt']) == case['expected'],
            final_metadata_delta=updates == case['metadata'],
            final_client_flag=cached_final == case['expected'],
            position_preserved=all(vector(row[k]) == [15.5, 85.0, 15.5]
                                   for k in ('before_pos', 'final_pos')),
            zero_motion=vector(row['final_motion']) == [0.0, 0.0, 0.0])
        for name, passed in checks.items():
            expected_failure = baseline and (
                (case['id'] in {'black-to-blue', 'blue-to-black', 'remove-blue-flag'}
                 and name in {'final_metadata_delta', 'final_client_flag'})
                or (case['id'] == 'remove-blue-flag' and name == 'final_server_flag'))
            assert passed != expected_failure, (row['case'], name, passed, updates)
            total += 1
            if not passed:
                failed.append((row['case'], name))
    assert len(failed) == (14 if baseline else 0)
    return {'passed': total - len(failed), 'total': total, 'failed': failed}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()),
                                  '--baseline' in sys.argv)))
