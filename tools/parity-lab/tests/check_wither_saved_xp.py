"""Check XP eligibility after recreating a mob from its actual serialized NBT."""
import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-saved-xp/cases.json'


def uuid(raw):
    match = re.search(r'\[I;([^\]]+)\]', raw)
    return tuple(int(part) for part in match[1].split(',')) if match else None


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
        assert (row['trial'], row['case'], row['entity']) == (trial, case['id'], case['entity'])
        end = next(i for i, e in enumerate(row['events']) if e['command'] ==
                   'execute if entity @a[gamemode=creative]') + 1
        events = row['events'][:end]
        gameplay = [e['command'] for e in events if e['command'] != 'time query gametime']
        # This is the saved payload itself, with only the entity identity removed.
        snapshot = re.search(r'(\{.*\})', next(e['raw'] for e in events if e['command'] ==
                            'data get entity @e[tag=pp_boss,limit=1]'), re.S)[0]
        assert snapshot == row['snapshot']
        payload = re.sub(r'\bUUID\s*:\s*\[I;[^\]]+\]\s*,?\s*', '', snapshot)
        payload = re.sub(r',\s*}', '}', payload)
        assert payload == row['restored_payload']
        restore_command = f"summon minecraft:{case['entity']} 15 80 15 " + payload
        assert restore_command in gameplay
        if case['attacker'] == 'player':
            assert 'damage @e[tag=pp_boss,limit=1] 2 minecraft:player_attack by @p' in gameplay
        elif case['attacker'] == 'wolf':
            assert 'damage @e[tag=pp_boss,limit=1] 2 minecraft:mob_attack by @e[tag=pp_attacker,limit=1]' in gameplay
        for wait in [case['before'], case['after']]:
            if wait:
                assert f'tick step {wait}' in gameplay
        assert 'damage @e[tag=pp_boss,limit=1] 1000 minecraft:generic_kill' in gameplay
        checks = dict(row['checks'])
        checks['new_identity'] = uuid(row['old_uuid']) != uuid(row['new_uuid'])
        health = re.search(r'\bHealth\s*:\s*([^,}]+)', snapshot)[1]
        checks['accepted_hit'] = float(health.rstrip('f')) < case['health'] if case['attacker'] else float(health.rstrip('f')) == case['health']
        saved_time = re.search(r'\blast_hurt_by_player_memory_time\s*:\s*(-?\d+)', snapshot)
        saved_player = re.search(r'\blast_hurt_by_player\s*:\s*(\[I;[^\]]+\])', snapshot)
        remembered = bool(case['attacker']) and case['before'] <= 100
        checks['saved_memory'] = (int(saved_time[1]) if saved_time else None) == (100 - case['before'] if remembered else None)
        checks['saved_player'] = bool(saved_player) == remembered
        if remembered and case['attacker'] == 'wolf':
            checks['wolf_owner'] = saved_player is not None and uuid(saved_player[1]) == (1234, 5678, 9012, 3456)
        checks['restored_memory'] = (row['restored_memory'].endswith(': ' + str(100 - case['before']))) if remembered else 'entity data:' not in row['restored_memory']
        checks['restored_player'] = uuid(row['restored_player']) == (uuid(saved_player[1]) if saved_player else None)
        xp_query = next(e['raw'] for e in events if e['command'] == 'execute if entity @e[type=minecraft:experience_orb]')
        xp_present = 'Test passed' in xp_query
        assert xp_present == row['xp_present']
        checks['saved_xp'] = xp_present == case['expected_xp']
        checks['xp_nbt'] = ('Experience Orb has the following entity data:' in row['xp_nbt']) == xp_present
        # Runtime snapshots differ between servers; require exact payload restoration above.
        # Compare every other command, normalizing only the saved-payload/health arguments.
        gameplay = [cmd.replace(payload, '<saved-nbt>') if cmd == restore_command else
                    cmd.replace('nbt={Health:' + health, 'nbt={Health:<saved-health>')
                    for cmd in gameplay]
        commands[key] = hashlib.sha256(json.dumps(gameplay).encode()).hexdigest()
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
