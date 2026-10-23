"""Check natural Wither navigation, with charging and NoAI controls."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/wither-flying-control/cases.json'


def vector(raw, key):
    match = re.search(r'\b' + key + r': \[([^\]]+)\]', raw)
    return [float(v.strip().removesuffix('d')) for v in match[1].split(',')] if match else []


def check(report):
    spec = json.loads(FIXTURE.read_text())
    reference = json.loads((FIXTURE.parent / 'vertical-motion.json').read_text())
    checks = {
        'complete': report['complete'] and report['stopped'] and report['cleanup_passed'],
        'fixture': report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'cleanup ticks': report['cleanup_ticks'] == 26,
    }
    cases = {f"{trial}-{case['id']}": case for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    checks['cases'] = [row['case'] for row in report['rows']] == list(cases)
    commands = [e['command'] for e in report['setup']]
    for row in report['rows']:
        name = row['case']
        case = cases[name]
        def record(label, value):
            checks[name + ': ' + label] = bool(value)
        required = {'client_alive', 'boss_alive', 'target_alive', 'player_creative', 'no_environment_error'}
        record('environment controls', set(row['checks']) == required and all(row['checks'].values()))
        record('controlled ticks', row['verified_ticks'] == 25 + spec['ticks'])
        record('samples', [s['tick'] for s in row['samples']] == list(range(1, spec['ticks'] + 1)))
        spawns = [p['detail'] for p in row['packets'] if p['packet'] == 'ClientboundAddEntityPacket']
        record('tracked Wither', sum('type=WITHER,' in p for p in spawns) == 1)
        boss = [p for p in spawns if 'type=WITHER,' in p]
        boss_id = re.search(r'entityId=(\d+)', boss[0])[1] if boss else '-1'
        metadata = [p['detail'] for p in row['packets'] if p['packet'] == 'ClientboundSetEntityDataPacket' and re.search(r'entityId=' + boss_id + r'\b', p['detail'])]
        gravity_updates = [value == 'true' for packet in metadata for value in re.findall(r'EntityMetadata\(id=5, type=[^,]+, value=(true|false)\)', packet)]
        record('navigation no-gravity metadata', gravity_updates == [True] if case['flying'] else not any(gravity_updates))
        for sample in row['samples']:
            raw = sample['nbt']
            prefix = str(sample['tick']) + ' '
            invul = re.search(r'\bInvul: (-?\d+)', raw)
            record(prefix + 'spawn phase', invul and int(invul[1]) == max(0, case['invul'] - sample['tick']))
            health = re.search(r'\bHealth: ([\d.]+)f', raw)
            record(prefix + 'health', health and float(health[1]) == case['health'])
            pos, motion = vector(raw, 'Pos'), vector(raw, 'Motion')
            record(prefix + 'finite motion in arena', len(pos) == len(motion) == 3 and all(math.isfinite(v) for v in pos + motion) and 0 < pos[0] < 32 and 79 < pos[1] < 120 and 0 < pos[2] < 32)
            expected = reference['cases'][case['id']][sample['tick'] - 1]
            record(prefix + 'vertical flight matches vanilla', len(pos) == len(motion) == 3 and abs(pos[1] - expected['y']) < reference['tolerance'] and abs(motion[1] - expected['velocity_y']) < reference['tolerance'])
        first = vector(row['samples'][0]['nbt'], 'Pos')
        first_motion = vector(row['samples'][0]['nbt'], 'Motion')
        start_y = spec['boss_position'][1]
        if case['id'] == 'climb':
            record('first navigation tick climbs', len(first) == 3 and first[1] > start_y)
            record('first navigation velocity climbs', len(first_motion) == 3 and 0 < first_motion[1] < 0.02)
        elif case['id'] == 'descend':
            record('first navigation tick uses controlled descent', len(first) == 3 and start_y - 0.02 < first[1] < start_y)
            record('first navigation velocity uses controlled descent', len(first_motion) == 3 and -0.02 < first_motion[1] < 0)
        elif case['noai']:
            record('NoAI holds position', all(vector(s['nbt'], 'Pos') == spec['boss_position'] for s in row['samples']))
        commands.extend(e['command'] for e in row['events'] if e['command'] != 'time query gametime')
    commands.extend(e['command'] for e in report['cleanup_events'] if e['command'] != 'time query gametime')
    # Descending navigation has an independently reproduced waypoint-input error.
    # Retain its failures in the full result; report the bounded climb/control
    # regression separately so it cannot be mistaken for complete flight parity.
    scoped = {key: value for key, value in checks.items() if not re.match(r'\d+-descend:', key)}
    return dict(passed=sum(checks.values()), total=len(checks), failures=[k for k, v in checks.items() if not v], climb_and_controls=dict(passed=sum(scoped.values()), total=len(scoped), failures=[k for k, v in scoped.items() if not v]), commands_sha256=hashlib.sha256(json.dumps(commands).encode()).hexdigest(), checks=checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['failures']))
