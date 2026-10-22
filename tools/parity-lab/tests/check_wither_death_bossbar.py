"""Check actual observer packets around a Wither's 20-tick death animation."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/wither-death-bossbar/cases.json'


def check(report):
    spec = json.loads(FIXTURE.read_text())
    checks = {}
    checks['complete'] = report['complete'] and report['stopped'] and report['cleanup_passed']
    checks['fixture'] = report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    expected = {f"{trial}-{case['id']}": case for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    checks['cases'] = [row['case'] for row in report['rows']] == list(expected)
    commands = []
    for row in report['rows']:
        name = row['case']
        case = expected[name]
        def record(label, value):
            checks[name + ': ' + label] = bool(value)
        for label, value in row['checks'].items():
            record(label, value)
        record('controlled ticks', row['verified_ticks'] == 53)
        health = re.search(r'entity data: ([0-9.]+)f', row['initial_health'])
        record('initial health', health is not None and float(health[1]) == 300.0)
        numbers = re.search(r'\[([^]]+)\]', row['initial_pos'])
        pos = [float(x.strip().rstrip('d')) for x in numbers[1].split(',')] if numbers else []
        record('initial arena position', len(pos) == 3 and 14 < pos[0] < 16 and 83 < pos[1] < 86 and 14 < pos[2] < 16)
        record('lethal damage accepted', 'Applied 1000' in row['kill_result'])
        spawns = [p['detail'] for p in row['spawn_packets'] if p['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER,' in p['detail']]
        record('one initial Wither spawn', len(spawns) == 1)
        boss = int(re.search(r'entityId=(\d+)', spawns[0])[1]) if spawns else -1
        bars = [p['detail'] for p in row['spawn_packets'] if p['packet'] == 'ClientboundBossEventPacket']
        adds = [s for s in bars if 'action=ADD,' in s]
        record('one initial bossbar', len(adds) == 1)
        uid = re.search(r'uuid=([^,]+)', adds[0])[1] if adds else 'missing'
        active = False
        progress = None
        tracked = bool(spawns)
        def consume(packets):
            nonlocal active, progress, tracked
            for packet in packets:
                text = packet['detail']
                if packet['packet'] == 'ClientboundBossEventPacket' and 'uuid=' + uid + ',' in text:
                    if 'action=REMOVE,' in text:
                        active = False
                    if 'action=ADD,' in text:
                        active = True
                    if 'action=ADD,' in text or 'action=UPDATE_HEALTH,' in text:
                        progress = float(re.search(r', health=([\d.Ee+-]+)', text)[1])
                if packet['packet'] == 'ClientboundAddEntityPacket' and re.search(r'entityId=' + str(boss) + r'\b', text):
                    tracked = True
                if packet['packet'] == 'ClientboundRemoveEntitiesPacket':
                    ids = [int(x) for x in re.search(r'entityIds=\[([^]]*)', text)[1].split(',') if x.strip()]
                    if boss in ids:
                        tracked = False
        consume(row['spawn_packets'])
        before = progress
        record('initial visible progress', active and before is not None and 0 < before <= 1)
        record('stages', [stage['tick'] for stage in row['stages']] == spec['death_ticks'])
        death_metadata = False
        for stage in row['stages']:
            tick = stage['tick']
            consume(stage['packets'])
            death_metadata |= any(p['packet'] == 'ClientboundSetEntityDataPacket' and re.search(r'entityId=' + str(boss) + r'\b', p['detail']) and re.search(r'EntityMetadata\(id=9, type=[^,]+, value=0\.0\)', p['detail']) for p in stage['packets'])
            visible = tick < 20 and not (case['move'] and tick == 4)
            record(f'tick{tick} bossbar membership', active == visible)
            record(f'tick{tick} entity tracking', tracked == visible)
            record(f'tick{tick} progress retained', progress == before)
            record(f'tick{tick} no death progress update', not any(p['packet'] == 'ClientboundBossEventPacket' and 'uuid=' + uid + ',' in p['detail'] and 'action=UPDATE_HEALTH,' in p['detail'] for p in stage['packets']))
            expected_x = spec['outside_x'] if case['move'] and tick == 4 else 15.0
            position = re.search(r'\[([^]]+)\]', stage['player_pos'])
            position = [float(x.strip().rstrip('d')) for x in position[1].split(',')] if position else []
            record(f'tick{tick} observer position', position == [expected_x, 84.0, 15.0])
            if tick == 1:
                record('observer received zero health', death_metadata)
        commands.extend(e['command'] for e in row['events'] if e['command'] != 'time query gametime')
    checks['cleanup ticks'] = report['cleanup_ticks'] == 26
    commands.extend(e['command'] for e in report['cleanup_events'] if e['command'] != 'time query gametime')
    return dict(passed=sum(checks.values()), total=len(checks), failures=[k for k, v in checks.items() if not v], commands_sha256=hashlib.sha256(json.dumps(commands).encode()).hexdigest(), checks=checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['failures']))
