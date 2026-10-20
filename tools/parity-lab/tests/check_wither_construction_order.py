"""Check Wither construction clearing order against official 26.3 arena evidence."""

import hashlib
import json
from pathlib import Path
import re
import sys

FIXTURE = Path(__file__).parents[1] / 'fixtures/wither-construction-order/cases.json'


def destruction_sequence(row):
    sequence = []
    for packet in row['destroy_effects']:
        detail = packet['detail']
        assert packet['packet'] == 'ClientboundLevelEventPacket'
        assert 'event=PARTICLES_AND_SOUND_DESTROY_BLOCK,' in detail
        assert 'broadcast=false' in detail
        position = list(map(int, re.search(r'position=\((-?\d+), (-?\d+), (-?\d+)\)', detail).groups()))
        state = int(re.search(r'(?: stateId=|blockState=)(\d+)', detail)[1])
        sequence.append([position, state])
    return sequence


def check_report(report, baseline=False):
    spec = json.loads(FIXTURE.read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['fixture_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert [e['command'] for e in report['setup']] == spec['setup']
    expected_rows = [(trial, case) for trial in range(1, spec['trials'] + 1) for case in spec['cases']]
    assert len(report['rows']) == len(expected_rows)
    failures = []
    total = 0
    stimuli = {}
    for row, (trial, case) in zip(report['rows'], expected_rows):
        assert row['case'] == f"{trial}-{case['id']}"
        commands = [e['command'] for e in row['events'] if e['command'] != 'time query gametime']
        assert commands.count('tick step 6') == 1
        assert row['verified_ticks'] == 31
        assert sum(int(c.split()[-1]) for c in commands if c.startswith('tick step ')) == 31
        dispenser = [case['last'], 83, 16] if case['axis'] == 'x' else [15, 83, case['last'] + 1]
        assert commands.count('item replace block ' + ' '.join(map(str, dispenser)) +
                              ' container.0 with minecraft:wither_skeleton_skull') == 1
        stimuli[row['case']] = hashlib.sha256(json.dumps(commands).encode()).hexdigest()
        assert stimuli[row['case']] == row['gameplay_sha256']
        for name, passed in row['checks'].items():
            assert passed is True, (row['case'], name)
            total += 1
        consumed = {tuple(v['position']): spec['vanilla_state_ids'][v['block']] for v in row['consumed']}
        assert len(consumed) == 7
        # The matched first column depends on the final skull, as recorded on vanilla.
        expected = []
        columns = [14, 15, 16] if case['last'] == 14 else [16, 15, 14]
        for along, height in [(column, y) for column in columns for y in [83, 82, 81]]:
            position = [along, height, 15] if case['axis'] == 'x' else [15, height, along]
            expected.append([position, consumed.get(tuple(position), spec['vanilla_state_ids']['air'])])
        if destruction_sequence(row) != expected:
            failures.append([row['case'], 'nine_cell_clearing_sequence'])
        total += 1
    assert len(failures) == (len(expected_rows) if baseline else 0), failures
    return {'passed': total - len(failures), 'total': total, 'failed': failures, 'command_sha256': stimuli}


if __name__ == '__main__':
    print(json.dumps(check_report(json.loads(Path(sys.argv[1]).read_text()), '--baseline' in sys.argv)))
