"""Check isolated sitting-dragon cloud packets against the official 26.3 server."""
import hashlib
import json
from pathlib import Path
import re


def check(path, target):
    report = json.loads(Path(path).read_text())
    assert report['complete'] and report['stopped'] and report['cleanup_passed']
    assert report['target'] == target and len(report['rows']) == 6
    failures, particles, stimuli = [], {}, {}
    for row in report['rows']:
        assert all(row['checks'].values()), (row['case'], row['checks'])
        assert row['verified_ticks'] == 31
        position = row['player_position'].rsplit('[', 1)[1].rstrip(']')
        assert [float(v.strip().rstrip('d')) for v in position.split(',')] == [25.5, 100.0, 25.5]
        commands = [e['command'] for e in row['events']
                    if e['command'] != 'time query gametime']
        digest = hashlib.sha256(json.dumps(commands).encode()).hexdigest()
        assert row['gameplay_sha256'] == digest
        stimuli[row['case']] = digest
        metadata = [p['detail'] for p in row['packets']
                    if p['packet'] == 'ClientboundSetEntityDataPacket']
        particle_values = [s[s.index('Particle(type='):]
                           for s in metadata if 'Particle(type=' in s]
        particles[row['case']] = particle_values
        if row['spec']['id'] == 'breathing':
            spawns = [p['detail'] for p in row['packets']
                      if p['packet'] == 'ClientboundAddEntityPacket'
                      and 'type=AREA_EFFECT_CLOUD,' in p['detail']]
            assert len(spawns) == 1, (row['case'], spawns)
            assert 'x=16.5, y=100.0, z=7.5,' in spawns[0]
            entity_id = re.search(r'entityId=(\d+)', spawns[0])[1]
            cloud_metadata = [s for s in metadata
                              if re.search(r'entityId=' + entity_id + r',', s)]
            values = [s for s in cloud_metadata if 'Particle(type=' in s]
            assert values, (row['case'], cloud_metadata)
            expected = 'Particle(type=DRAGON_BREATH, data=PowerParticleData(power=1.0))'
            if not all(expected in value for value in values):
                failures.append(row['case'])
        else:
            # The ordinary vanilla cloud omits its default ENTITY_EFFECT value.
            assert not any('DRAGON_BREATH' in value for value in particle_values)
            assert all('ENTITY_EFFECT' in value for value in particle_values)
    assert failures == (['1-breathing', '2-breathing'] if target == 'baseline' else []), failures
    return {'passed': 6 - len(failures), 'total': 6, 'failures': failures,
            'stimulus_sha256': stimuli, 'particles': particles,
            'controlled_ticks': sum(r['verified_ticks'] for r in report['rows']),
            'binary_sha256': report.get('binary_sha256'),
            'fixture_sha256': report['fixture_sha256'],
            'directory': report['directory']}
