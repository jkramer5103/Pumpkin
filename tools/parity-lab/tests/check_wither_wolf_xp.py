"""Check wolf-attributed XP against observed vanilla mob deaths."""
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-wolf-xp/cases.json'


def check_report(report, *, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    expected = [(trial, case) for trial in range(1, spec['trials'] + 1)
                for case in spec['cases']]
    assert len(report['rows']) == len(expected)
    passed = total = 0
    failed, commands = [], {}
    for row, (trial, case) in zip(report['rows'], expected):
        key = f"{trial}-{case['id']}"
        assert (row['trial'], row['case'], row['entity'], row['wait']) == (
            trial, case['id'], case['entity'], case['wait'])
        end = next(i for i, event in enumerate(row['events']) if event['command'] ==
                   'execute if entity @a[gamemode=creative]') + 1
        events = row['events'][:end]
        gameplay = [e['command'] for e in events if e['command'] != 'time query gametime']
        assert f"damage @e[tag=pp_boss,limit=1] {case['amount']} minecraft:mob_attack by @e[tag=pp_attacker,limit=1]" in gameplay
        assert f"summon minecraft:{case['attacker']} 25 80 25 " in next(
            cmd for cmd in gameplay if cmd.startswith('summon ') and 'pp_attacker' in cmd)
        if case['wait']:
            assert f"tick step {case['wait']}" in gameplay
        if case['pre_player'] is not None:
            assert 'damage @e[tag=pp_boss,limit=1] 2 minecraft:player_attack by @p' in gameplay
            if case['pre_player']:
                assert f"tick step {case['pre_player']}" in gameplay
        assert ('damage @e[tag=pp_boss,limit=1] 1000 minecraft:generic_kill' in gameplay) != case['lethal']
        checks = dict(row['checks'])
        # Re-read actual health and ownership evidence rather than trusting probe booleans.
        health = lambda raw: float(re.search(r'entity data: (-?[0-9.]+)f', raw)[1])
        if case['lethal']:
            checks['health_change'] = (row['health_after_hit'] == 'No entity was found' or health(row['health_after_hit']) == 0)
        else:
            checks['health_change'] = ((health(row['health_after_hit']) < health(row['health_before_hit'])) == case['expected_hit'])
        owner = re.search(r'\[I;([^\]]+)\]', row['owner_nbt'])
        checks['owner_present'] = bool(owner) == bool(case['owner'])
        if case['owner'] == 'online':
            checks['owner_matches_player'] = owner[1] == re.search(r'\[I;([^\]]+)\]', row['player_uuid'])[1]
        elif case['owner'] == 'offline':
            checks['offline_owner_uuid'] = [int(x) for x in owner[1].split(',')] == [1234, 5678, 9012, 3456]
        xp_query = next(e['raw'] for e in events if e['command'] ==
                        'execute if entity @e[type=minecraft:experience_orb]')
        xp_present = 'Test passed' in xp_query
        assert xp_present == row['xp_present']
        checks['wolf_xp'] = xp_present == case['expected_xp']
        checks['xp_nbt'] = ('Experience Orb has the following entity data:' in row['xp_nbt']) == xp_present
        if case['owner'] == 'online':
            player_uuid = re.search(r'\[I;[^\]]+\]', row['player_uuid'])[0]
            assert 'data merge entity @e[tag=pp_attacker,limit=1] {Owner:' + player_uuid + '}' in gameplay
            gameplay = [cmd.replace(player_uuid, '<player-uuid>') for cmd in gameplay]
        commands[key] = hashlib.sha256(json.dumps(gameplay).encode()).hexdigest()
        assert commands[key] == row['gameplay_sha256']
        for name, value in checks.items():
            total += 1
            passed += bool(value)
            if not value:
                failed.append([key, name])
    if not baseline:
        assert not failed, failed
    return dict(passed=passed, total=total, failed=failed, command_sha256=commands)


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        result = check_report(json.loads(Path(filename).read_text()))
        print(filename, result['passed'], '/', result['total'])
