"""Check pillar regeneration with surviving original End crystals."""
import json
import pathlib
import re
import sys


def count_crystals(raw):
    return len(re.findall('has the following entity data:', raw))


def check(path, baseline=False):
    report = json.loads(pathlib.Path(path).read_text())
    fixture = pathlib.Path(__file__).resolve().parents[1] / 'fixtures/dragon-respawn-surviving-pillars/cases.json'
    case = json.loads(fixture.read_text())
    rows = report['rows']
    assert report['stopped'] and report['initial_dragon_present'] and report['arena_ready']
    assert count_crystals(report['original_crystals']) == case['pillar_crystals']
    assert '10' in report['original_count_tag'] and 'pp_original' in report['original_count_tag']
    for index, row in enumerate(rows):
        assert row['step'] == index and row['ticks'] == case['ticks_per_step']
        if 'dragon' not in row:
            assert baseline and index == len(rows) - 1
            continue
        ticks = (index + 1) * case['ticks_per_step']
        rebuilt = max(0, min(case['pillar_crystals'],
                            (ticks - case['first_rebuild_tick']) // case['rebuild_interval'] + 1))
        assert count_crystals(row['originals']) == case['pillar_crystals'] - rebuilt
        expected_total = case['pillar_crystals'] + (case['portal_crystals'] if index < case['steps'] - 1 else 0)
        assert count_crystals(row['crystals']) == expected_total
        if index < case['steps'] - 1:
            assert row['dragon'] == 'Test failed' and 'Test passed' in row['participants']
    if baseline:
        assert not report['complete'] and len(rows) == 8 and 'dragon' not in rows[-1]
        clocks = [event['raw'] for event in report['events']
                  if event['command'] == 'time query gametime']
        assert len(clocks) > 20 and len(set(clocks[-20:])) == 1
        return {'stalled_at_first_pillar_rebuild': True,
                'completed_ritual_ticks': (len(rows) - 1) * case['ticks_per_step']}
    assert report['complete'] and report['client_alive'] and report['player_present']
    assert report['cleanup_passed'] and len(rows) == case['steps']
    assert 'Test passed' in rows[-1]['dragon'] and rows[-1]['participants'] == 'Test failed'
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
            'original_crystals_replaced': case['pillar_crystals'],
            'regenerated_crystals_vulnerable': case['pillar_crystals'],
            'continued_ticks': case['continuation_ticks']}


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1], '--baseline' in sys.argv[2:]), indent=2))
