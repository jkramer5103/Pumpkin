"""Compare consumed-block destruction payloads with the official 26.3 server."""

import hashlib
import json
from pathlib import Path
import re
import sys

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-construction-effects/cases.json'


def effect_states(row):
    states = {}
    for packet in row['destroy_effects']:
        detail = packet['detail']
        assert packet['packet'] == 'ClientboundLevelEventPacket'
        assert 'event=PARTICLES_AND_SOUND_DESTROY_BLOCK,' in detail or 'event=PARTICLES_DESTROY_BLOCK,' in detail
        assert 'broadcast=false' in detail
        position = tuple(map(int, re.search(r'position=\((-?\d+), (-?\d+), (-?\d+)\)', detail).groups()))
        state = int(re.search(r'(?: stateId=|blockState=)(\d+)', detail)[1])
        assert position not in states
        states[position] = state
    return states


def check_report(report, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert [e['command'] for e in report['setup']] == spec['setup']
    expected = [(trial, case) for trial in range(1, spec['trials'] + 1) for case in spec['cases']]
    assert len(report['rows']) == len(expected)
    failures = []
    total = 0
    stimuli = {}
    for row, (trial, case) in zip(report['rows'], expected):
        assert row['case'] == f"{trial}-{case['id']}"
        commands = [e['command'] for e in row['events'] if e['command'] != 'time query gametime']
        assert commands.count('tick step 6') == 1
        assert any(c.startswith('item replace block ') and c.endswith('container.0 with minecraft:wither_skeleton_skull') for c in commands)
        assert row['verified_ticks'] == 31
        assert sum(int(c.split()[-1]) for c in commands if c.startswith('tick step ')) == 31
        stimuli[row['case']] = hashlib.sha256(json.dumps(commands).encode()).hexdigest()
        assert stimuli[row['case']] == row['gameplay_sha256']
        for name, passed in row['checks'].items():
            assert passed is True, (row['case'], name)
            total += 1
        actual = effect_states(row)
        if not all('event=PARTICLES_AND_SOUND_DESTROY_BLOCK,' in p['detail'] for p in row['destroy_effects']):
            failures.append([row['case'], 'particles_and_sound'])
        total += 1
        assert len(row['consumed']) == 7
        for consumed in row['consumed']:
            position = tuple(consumed['position'])
            assert position in actual, (row['case'], position)
            expected_state = spec['vanilla_state_ids'][consumed['block']]
            if actual[position] != expected_state:
                failures.append([row['case'], list(position), expected_state, actual[position]])
            total += 1
    assert len(failures) == (48 if baseline else 0), failures
    return {'passed': total - len(failures), 'total': total, 'failed': failures, 'command_sha256': stimuli}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()), '--baseline' in sys.argv)))
