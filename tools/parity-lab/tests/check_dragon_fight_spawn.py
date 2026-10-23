"""Check the initial transform sent for a fight-created dragon."""
import json
import pathlib
import re
import sys


def check(path):
    report = json.loads(pathlib.Path(path).read_text())
    fixture = pathlib.Path(__file__).resolve().parents[1] / 'fixtures/dragon-fight-spawn/cases.json'
    case = json.loads(fixture.read_text())
    assert report['complete'] and report['stopped'] and report['arena_ready']
    assert report['initial_dragon_present'] and report['client_alive'] and report['player_present']
    assert report['cleanup_passed']
    packets = [p['detail'] for p in report['packets']
               if p['packet'] == 'ClientboundAddEntityPacket' and 'type=ENDER_DRAGON,' in p['detail']]
    assert len(packets) == 1, packets
    packet = packets[0]
    position = [float(re.search(r'(?:, )' + axis + r'=([-\d.]+)', packet)[1]) for axis in 'xyz']
    motion = [float(v) for v in re.search(r'movement=\(([^)]+)\)', packet)[1].split(',')]
    yaw = float(re.search(r', yaw=([-\d.]+)', packet)[1]) % 360.0
    pitch = float(re.search(r', pitch=([-\d.]+)', packet)[1])
    assert position == case['position'], position
    assert motion == case['motion'] and pitch == case['pitch']
    assert case['yaw_min'] <= yaw < case['yaw_max_exclusive'], yaw
    # A random vanilla yaw may legitimately be zero, including after packet quantization.
    assert re.search(r'entity data: ' + str(case['dragon_health']) + r'(?:\.0)?f', report['dragon_health'])
    assert re.search(r'entity data: ' + str(case['dragon_phase']) + r'$', report['observed_phase'])
    return {'spawn_position': position, 'spawn_yaw': yaw, 'spawn_pitch': pitch,
            'natural_fight_spawn': True, 'headless_only': True}


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1]), indent=2))
