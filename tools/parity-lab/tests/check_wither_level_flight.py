"""Compare Wither near-level flying waypoints with captured official motion."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/wither-level-flight/cases.json'


def vector(raw, key):
    match = re.search(r'\b' + key + r': \[([^\]]+)\]', raw)
    return [float(value.strip().removesuffix('d')) for value in match[1].split(',')] if match else []


def check(report):
    spec = json.loads(FIXTURE.read_text())
    reference = json.loads((FIXTURE.parent / 'vertical-motion.json').read_text())
    horizontal = json.loads((FIXTURE.parent / 'horizontal-motion.json').read_text())
    cases = {f"{trial}-{case['id']}": case for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    checks = {
        'complete and stopped': report['complete'] and report['stopped'],
        'cleanup': report['cleanup_passed'] and report['cleanup_ticks'] == 26,
        'fixture': report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'cases': [row['case'] for row in report['rows']] == list(cases),
        'setup': [event['command'] for event in report['setup']] == spec['setup'],
    }
    commands = [event['command'] for event in report['setup']]
    for row in report['rows']:
        name = row['case']
        case = cases[name]
        def record(label, value):
            checks[name + ': ' + label] = bool(value)
        required = {'client_alive', 'target_alive', 'player_creative', 'no_environment_error'}
        record('environment controls', set(row['checks']) == required and all(row['checks'].values()))
        record('controlled ticks', row['verified_ticks'] == 25 + spec['pre_ticks'] + spec['post_ticks'])
        actions = [event['command'] for event in row['events'] if event['command'] != 'time query gametime']
        record('spawn and transition', all(command in actions for command in case['spawn'] + case['transition']))
        spawns = [packet['detail'] for packet in row['packets'] if packet['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER,' in packet['detail']]
        record('tracked Wither', len(spawns) == 1)
        boss_id = re.search(r'entityId=(\d+)', spawns[0])[1] if spawns else '-1'
        metadata = [packet['detail'] for packet in row['packets'] if packet['packet'] == 'ClientboundSetEntityDataPacket' and re.search(r'entityId=' + boss_id + r'\b', packet['detail'])]
        updates = [value == 'true' for packet in metadata for value in re.findall(r'EntityMetadata\(id=5, type=[^,]+, value=(true|false)\)', packet)]
        # Metadata starts at vanilla's default false; redundant updates are harmless.
        def transitions(values):
            state = False
            result = []
            for value in values:
                if value != state:
                    result.append(value)
                    state = value
            return result
        record('gravity metadata transition', transitions(updates) == transitions(reference['cases'][case['id']]['gravity_updates']))
        for phase, ticks in [('before', spec['pre_ticks']), ('after', spec['post_ticks'])]:
            record(phase + ' samples', [sample['tick'] for sample in row[phase]] == list(range(1, ticks + 1)))
            for sample in row[phase]:
                prefix = f"{phase} {sample['tick']} "
                raw = sample['nbt']
                pos, motion = vector(raw, 'Pos'), vector(raw, 'Motion')
                record(prefix + 'finite motion in arena', len(pos) == len(motion) == 3 and all(math.isfinite(value) for value in pos + motion) and 0 < pos[0] < 32 and 79 < pos[1] < 120 and 0 < pos[2] < 32)
                expected = reference['cases'][case['id']][phase][sample['tick'] - 1]
                record(prefix + 'vertical motion matches vanilla', len(pos) == len(motion) == 3 and abs(pos[1] - expected['y']) < reference['tolerance'] and abs(motion[1] - expected['velocity_y']) < reference['tolerance'])
                expected_horizontal = horizontal['cases'][case['id']][phase][sample['tick'] - 1]
                record(prefix + 'horizontal motion matches vanilla', len(pos) == len(motion) == 3 and all(abs(actual - expected_horizontal[key]) < horizontal['tolerance'] for actual, key in [(pos[0], 'x'), (pos[2], 'z'), (motion[0], 'velocity_x'), (motion[2], 'velocity_z')]))
                record(prefix + 'health and phase', bool(re.search(r'\bHealth: 100(?:\.0)?f\b', raw)) and bool(re.search(r'\bInvul: ' + str(40 - sample['tick'] if case['id'] == 'charging-control' else 0) + r'\b', raw)))
        commands.extend(actions)
    commands.extend(event['command'] for event in report['cleanup_events'] if event['command'] != 'time query gametime')
    # Initial input is bounded to the first three ticks, before subsequent node
    # selection diverges. Keep the full eight-tick failures visible alongside it.
    initial_checks = {
        key: value for key, value in checks.items()
        if not re.search(r'-(?:level|near-level): after [4-8] vertical motion', key)
    }
    initial = dict(passed=sum(initial_checks.values()), total=len(initial_checks),
                   failures=[key for key, value in initial_checks.items() if not value])
    return dict(passed=sum(checks.values()), total=len(checks), failures=[key for key, value in checks.items() if not value], commands_sha256=hashlib.sha256(json.dumps(commands).encode()).hexdigest(), initial_input_and_controls=initial, checks=checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['failures']))
