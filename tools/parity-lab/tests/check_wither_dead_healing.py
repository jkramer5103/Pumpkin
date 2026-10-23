"""Check dead-target healing and corpse removal against official 26.3."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/wither-dead-healing/cases.json'


def number(raw):
    match = re.search(r'entity data: (-?[0-9.]+)[fs]?$', raw.strip())
    return float(match[1]) if match else None


def check(report):
    spec = json.loads(FIXTURE.read_text())
    checks = {
        'complete': report['complete'] and report['stopped'] and report['cleanup_passed'],
        'fixture': report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'warmup ticks': report['warmup_ticks'] == 106,
        'cleanup ticks': report['cleanup_ticks'] == 26,
    }
    expected = {f"{trial}-{case['id']}": case for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    checks['cases'] = [row['case'] for row in report['rows']] == list(expected)
    commands, health = [], {}
    for row in report['rows']:
        name = row['case']
        case = expected[name]
        for label, value in row['checks'].items():
            checks[name + ': ' + label] = bool(value)
        checks[name + ': ticks'] = row['verified_ticks'] == 46
        queries = [e['raw'] for e in row['events'] if e['command'] == 'time query gametime']
        checks[name + ': removal settled without extra ticks'] = len(queries) >= 2 and queries[-2] == queries[-1] == row['settled_gametime']
        checks[name + ': initial health'] = number(row['initial_health']) == case['health']
        checks[name + ': before health'] = number(row['before_health']) == (0 if case['kill'] else case['health'])
        checks[name + ': before death time'] = number(row['before_death_time']) == case['delay']
        if case['entity'] == 'wither':
            for stage in ('initial_invul', 'final_invul'):
                checks[name + ': ' + stage] = number(row[stage]) == case['invul']
        final = number(row['final_health'])
        health[name] = final
        checks[name + ': final health'] = final == case['expected_health']
        checks[name + ': final death time'] = number(row['final_death_time']) == (case['delay'] + spec['impact_ticks'] if case['kill'] else 0)
        checks[name + ': tick19 health'] = number(row['tick19_health']) == case['expected_health']
        checks[name + ': tick19 death time'] = number(row['tick19_death_time']) == (19 if case['kill'] else 0)
        checks[name + ': tick20 removal or living control'] = row['tick20_health'].strip() == 'No entity was found' if case['kill'] else number(row['tick20_health']) == case['expected_health']
        for stage in ('initial_pos', 'final_pos'):
            match = re.search(r'\[([^]]+)\]', row[stage])
            pos = [float(x.strip().rstrip('d')) for x in match[1].split(',')] if match else []
            checks[name + ': ' + stage] = len(pos) == 3 and all(abs(x - y) < 0.001 for x, y in zip(pos, [15.5, 80, 15.5]))
        packets = row['impact_packets']
        checks[name + ': real splash potion'] = row['projectile_before'].startswith('Splash Potion has the following entity data:')
        checks[name + ': real item use'] = sum(p['packet'] == 'ServerboundUseItemPacket' for p in packets) == 1
        checks[name + ': splash event'] = any(p['packet'] == 'ClientboundLevelEventPacket' and 'POTION_SPLASH' in p['detail'] for p in packets)
        if case['kill']:
            checks[name + ': lethal hit succeeded'] = 'Applied 1000' in row['kill_result']
            checks[name + ': death packet'] = any(p['packet'] == 'ClientboundEntityEventPacket' and 'event=LIVING_DEATH' in p['detail'] for p in packets)
        commands.extend(e['command'] for e in row['events'] if e['command'] != 'time query gametime')
    return {'passed': sum(checks.values()), 'total': len(checks), 'failures': [k for k, v in checks.items() if not v],
            'health': health, 'commands_sha256': hashlib.sha256(json.dumps(commands).encode()).hexdigest(), 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['failures']))
