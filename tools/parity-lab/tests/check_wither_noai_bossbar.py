"""Check Wither bossbar tracking while custom AI is disabled."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/wither-noai-bossbar/cases.json'


def check(report):
    spec = json.loads(FIXTURE.read_text())
    checks = {
        'complete': report['complete'] and report['stopped'] and report['cleanup_passed'],
        'fixture': report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
    }
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
        record('controlled ticks', row['verified_ticks'] == 49)
        record('stages', [s['stage'] for s in row['stages']] == ['initial', 'away', 'return'])
        initial, away, returned = row['stages']
        spawns = [p['detail'] for p in initial['packets'] if p['packet'] == 'ClientboundAddEntityPacket' and 'type=WITHER,' in p['detail']]
        record('initial Wither tracked', len(spawns) == 1)
        boss = int(re.search(r'entityId=(\d+)', spawns[0])[1]) if spawns else -1
        adds = [p['detail'] for p in initial['packets'] if p['packet'] == 'ClientboundBossEventPacket' and 'action=ADD,' in p['detail']]
        record('initial bossbar visible', len(adds) == 1)
        progress = [float(m[1]) for p in initial['packets'] if p['packet'] == 'ClientboundBossEventPacket' and (m := re.search(r'health=([0-9.Ee+-]+)', p['detail']))]
        expected_progress = 1.0 if case['noai'] or not case['invul'] else 1.0 - (case['invul'] - 4) / 220.0
        record('initial displayed progress', bool(progress) and abs(progress[-1] - expected_progress) < 1e-6)
        if case['noai']:
            record('NoAI does not update progress', not any(p['packet'] == 'ClientboundBossEventPacket' and 'action=UPDATE_HEALTH,' in p['detail'] for p in initial['packets']))
        uid = re.search(r'uuid=([^,]+)', adds[0])[1] if adds else 'missing'
        bars = [p['detail'] for p in away['packets'] if p['packet'] == 'ClientboundBossEventPacket' and 'uuid=' + uid + ',' in p['detail']]
        record('departure removes bossbar', sum('action=REMOVE,' in s for s in bars) == 1)
        visible = True
        for s in bars:
            if 'action=REMOVE,' in s:
                visible = False
            elif 'action=ADD,' in s:
                visible = True
        record('departure clears observer cache', not visible)
        dimension = 'minecraft:overworld'
        record('observer destination dimension', '"' + dimension + '"' in away['player_dimension'])
        record('observer returns to Overworld', '"minecraft:overworld"' in returned['player_dimension'])
        record('distance removes tracked entity', any(p['packet'] == 'ClientboundRemoveEntitiesPacket' and str(boss) in re.findall(r'\d+', p['detail']) for p in away['packets']))
        for stage in [away, returned]:
            prefix = stage['stage']
            health = re.search(r'entity data: ([0-9.]+)f', stage['boss_health'])
            record(prefix + ' boss remains alive', health is not None and float(health[1]) == 300.0)
            invul = re.search(r'entity data: (-?\d+)', stage['boss_invul'])
            record(prefix + ' spawn phase preserved', invul is not None and int(invul[1]) == (case['invul'] if case['noai'] else max(0, case['invul'] - (12 if stage['stage'] == 'away' else 20))))
        commands.extend(e['command'] for e in row['events'] if e['command'] != 'time query gametime')
    commands.extend(e['command'] for e in report['cleanup_events'] if e['command'] != 'time query gametime')
    checks['cleanup ticks'] = report['cleanup_ticks'] == 26
    return dict(passed=sum(checks.values()), total=len(checks), failures=[k for k, v in checks.items() if not v], commands_sha256=hashlib.sha256(json.dumps(commands).encode()).hexdigest(), checks=checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['failures']))
