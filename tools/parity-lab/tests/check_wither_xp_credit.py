"""Check real mob deaths around vanilla's player XP-credit expiry."""
import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-xp-credit/cases.json'


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
        assert f"tick step {case['wait']}" in gameplay
        assert ('damage @e[tag=pp_boss,limit=1] 1 minecraft:player_attack by @p' in
                gameplay) == case['credited']
        assert 'gamerule advance_time ' + str(case['advance_time']).lower() in gameplay
        assert ('time add 1000' in gameplay) == case['time_jump']
        assert 'damage @e[tag=pp_boss,limit=1] 1000 minecraft:generic_kill' in gameplay
        xp_query = next(e['raw'] for e in events if e['command'] ==
                        'execute if entity @e[type=minecraft:experience_orb]')
        xp_present = 'Test passed' in xp_query
        assert xp_present == row['xp_present']
        checks = dict(row['checks'])
        checks['xp_credit'] = xp_present == case['expected_xp']
        checks['xp_nbt'] = ('Experience Orb has the following entity data:' in
                            row['xp_nbt']) == xp_present
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
