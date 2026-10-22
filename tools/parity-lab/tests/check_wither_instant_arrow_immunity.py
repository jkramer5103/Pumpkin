"""Check Wither instant-arrow immunity using real health and packet observations."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/wither-instant-arrow-immunity/cases.json'


def number(raw):
    match = re.search(r'entity data: ([0-9.]+)f', raw)
    return float(match[1]) if match else None


def check(report):
    spec = json.loads(FIXTURE.read_text())
    checks = {'complete': report['complete'] and report['stopped'] and report['cleanup_passed'],
              'fixture': report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()}
    expected = {f"{trial}-{case['id']}": case for trial in range(1, spec['trials'] + 1) for case in spec['cases']}
    checks['cases'] = [row['case'] for row in report['rows']] == list(expected)
    checks['warmup ticks'] = report['warmup_ticks'] == 106
    checks['cleanup ticks'] = report['cleanup_ticks'] == 26
    commands = []
    health = {}
    for row in report['rows']:
        name = row['case']
        case = expected[name]
        for label, value in row['checks'].items():
            checks[name + ': ' + label] = bool(value)
        checks[name + ': ticks'] = row['verified_ticks'] == 34
        checks[name + ': initial health'] = number(row['initial_health']) == case['health']
        final = number(row['final_health'])
        # Fixed observations from official 26.3; include a plain-arrow damage control.
        expected_health = 200.0 if case.get('invul') else 199.14
        if case['entity'] == 'sheep':
            expected_health = 8.0 if case['effect'] == 'instant_health' else 2.0
        health[name] = final
        checks[name + ': final health'] = final is not None and abs(final - expected_health) < 0.0001
        for stage in ('initial_pos', 'final_pos'):
            match = re.search(r'\[([^]]+)\]', row[stage])
            pos = [float(x.strip().rstrip('d')) for x in match[1].split(',')] if match else []
            checks[name + ': ' + stage] = len(pos) == 3 and 14 < pos[0] < 17 and 84 < pos[1] < 87 and 14 < pos[2] < 17
        adds = [p['detail'] for p in row['impact_packets'] if p['packet'] == 'ClientboundAddEntityPacket' and 'type=ARROW,' in p['detail']]
        checks[name + ': real arrow'] = len(adds) == 1
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
