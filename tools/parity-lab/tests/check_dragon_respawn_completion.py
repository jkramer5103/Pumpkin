"""Check the full ritual's final tick, crystal consumption and world liveness."""
import json
import pathlib
import re
import sys


def check(path, baseline=False):
    report = json.loads(pathlib.Path(path).read_text())
    fixture = pathlib.Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-completion/cases.json'
    case = json.loads(fixture.read_text())
    rows = report['rows']
    assert report['stopped'] and report['initial_dragon_present']
    assert len(rows) == case['steps']
    assert all(row['step'] == index and row['ticks'] == case['ticks_per_step']
               for index, row in enumerate(rows))
    assert all(row['dragon'] == 'Test failed' and 'Test passed' in row['participants']
               for row in rows[:-1])
    assert all(len(re.findall('has the following entity data:', row['crystals'])) >= 4
               for row in rows[:-1])
    assert len(re.findall('has the following entity data:', rows[0]['crystals'])) == case['portal_crystals']
    assert len(re.findall('has the following entity data:', rows[-2]['crystals'])) == case['portal_crystals'] + case['pillar_crystals']
    if baseline:
        assert not report['complete'] and 'dragon' not in rows[-1]
        clocks = [event['raw'] for event in report['events']
                  if event['command'] == 'time query gametime']
        assert len(clocks) > 20 and len(set(clocks[-20:])) == 1
        return {'stalled_on_final_step': True, 'completed_steps': len(rows) - 1}
    assert report['complete'] and report['client_alive'] and report['player_present']
    assert report['cleanup_passed']
    final = rows[-1]
    assert 'Test passed' in final['dragon'] and final['participants'] == 'Test failed'
    assert len(re.findall('has the following entity data:', final['crystals'])) == case['pillar_crystals']
    assert re.search(r'entity data: 200(?:\.0)?f', report['dragon_health'])
    assert len(re.findall(r'Applied 1(?:\.0)? damage to End Crystal', report['pillar_damage'])) == case['pillar_crystals']
    assert report['pillars_destroyed'] == 'Test passed'
    clock = lambda raw: int(re.fullmatch(r'The game time is (\d+) tick\(s\)', raw)[1])
    assert clock(report['continuation_clock_after']) - clock(report['continuation_clock_before']) == case['continuation_ticks']
    assert 'Test passed' in report['same_dragon']
    assert any(packet['packet'] == 'ClientboundAddEntityPacket' and 'type=ENDER_DRAGON,' in packet['detail']
               for packet in report['packets'])
    assert any(packet['packet'] == 'ServerboundUseItemOnPacket' for packet in report['packets'])
    return {'ritual_ticks': case['steps'] * case['ticks_per_step'],
            'pillar_crystals_consumed_after_damage': case['pillar_crystals'],
            'continued_ticks': case['continuation_ticks']}


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1], '--baseline' in sys.argv[2:]), indent=2))
