"""Private fresh-world fixture that loads one bounded chunk on current Pumpkin.

The test loader is explicit: forceload alone does not generate upstream chunks.
No existing world is copied or overwritten. Original NBT fixture, not game data.
"""
import gzip
import json
import struct


def _text(value):
    data = value.encode('utf-8')
    return struct.pack('>H', len(data)) + data


def _payload(kind, value):
    if kind == 1: return struct.pack('>b', value)
    if kind == 3: return struct.pack('>i', value)
    if kind == 4: return struct.pack('>q', value)
    if kind == 8: return _text(value)
    if kind == 9:
        subtype, items = value
        return bytes([subtype]) + struct.pack('>i', len(items)) + b''.join(_payload(subtype, v) for v in items)
    if kind == 10:
        return b''.join(bytes([t]) + _text(k) + _payload(t,v) for k,(t,v) in value.items()) + b'\0'
    raise ValueError('Unsupported fixture NBT type')


def seed_arena(directory):
    world = directory / 'world'
    if world.exists():
        raise FileExistsError('Refusing to replace existing scratch world')
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(b'\x0a\0\0' + _payload(10, value), mtime=0))
    layers = [{'height': (3,h), 'block': (8,b)} for h,b in
              [(1,'minecraft:bedrock'), (126,'minecraft:dirt'), (1,'minecraft:grass_block')]]
    generator = {'type': (8,'minecraft:flat'), 'settings': (10,{
        'biome': (8,'minecraft:plains'), 'layers': (9,(10,layers)), 'lakes': (1,0),
        'features': (1,0), 'structure_overrides': (9,(8,[]))})}
    write(world / 'data/minecraft/world_gen_settings.dat', {'DataVersion': (3,4903),
        'seed': (4,123456789), 'generate_structures': (1,0), 'bonus_chest': (1,0),
        'dimensions': (10,{'minecraft:overworld': (10,{
            'type': (8,'minecraft:overworld'), 'generator': (10,generator)})})})
    write(world / 'level.dat', {'Data': (10,{'DataVersion': (3,4903), 'version': (3,19133),
        'LevelName': (8,'world'), 'allowCommands': (1,1), 'SpawnX': (3,0), 'SpawnY': (3,64), 'SpawnZ': (3,0),
        'DataPacks': (10,{'Enabled': (9,(8,['vanilla','file/parity_arena'])), 'Disabled': (9,(8,[]))}),
        'WorldGenSettings': (10,{'seed': (4,123456789)})})})
    pack = world / 'datapacks/parity_arena'
    (pack / 'data/parity_arena/test_instance').mkdir(parents=True)
    (pack / 'pack.mcmeta').write_text(json.dumps({'pack': {'pack_format': 1, 'description': 'Parity scratch arena loader'}}))
    (pack / 'data/parity_arena/test_instance/load.json').write_text(json.dumps({
        'type': 'minecraft:block_based', 'environment': 'minecraft:default',
        'structure': 'parity_arena:load', 'max_ticks': 1, 'max_attempts': 1,
        'required_successes': 1, 'manual_only': False}))
    write(pack / 'data/parity_arena/structure/load.nbt', {'size': (9,(3,[1,1,1])),
        'palette': (9,(10,[{'Name': (8,'minecraft:stone')}])),
        'blocks': (9,(10,[{'pos': (9,(3,[0,0,0])), 'state': (3,0)}]))})
