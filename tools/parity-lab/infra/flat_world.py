"""Write an empty flat-world seed using the official Pumpkin release's NBT schema.

The release accepts DataVersion <=4903 despite advertising the 26.3 protocol.
This creates new metadata at its own supported version; it does not downgrade or
rewrite an existing vanilla/Pumpkin world. No chunks or entities are imported.
"""
import gzip
from pathlib import Path
import struct


def string(value):
    raw = value.encode('utf-8')
    return struct.pack('>H', len(raw)) + raw


def payload(kind, value):
    if kind == 1:
        return struct.pack('>b', value)
    if kind == 3:
        return struct.pack('>i', value)
    if kind == 4:
        return struct.pack('>q', value)
    if kind == 8:
        return string(value)
    if kind == 9:
        subtype, items = value
        return bytes([subtype])+struct.pack('>i', len(items))+b''.join(payload(subtype, x) for x in items)
    if kind == 10:
        return b''.join(bytes([t])+string(k)+payload(t,v) for k,(t,v) in value.items())+b'\0'
    raise ValueError('Unsupported seed NBT tag')


def write_nbt(path, compound):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(b'\x0a\x00\x00'+payload(10,compound),mtime=0))
    path.chmod(0o600)


def seed_pumpkin_flat(world):
    world = Path(world)
    if (world/'level.dat').exists():
        raise FileExistsError('Refusing to replace existing world metadata')
    layers = [{'height':(3,h),'block':(8,b)} for h,b in [
        (1,'minecraft:bedrock'),(2,'minecraft:dirt'),(1,'minecraft:grass_block')]]
    generator = {'type':(8,'minecraft:flat'),'settings':(10,{
        'biome':(8,'minecraft:plains'),'layers':(9,(10,layers)),
        'lakes':(1,0),'features':(1,0),'structure_overrides':(9,(8,[]))})}
    settings = {'DataVersion':(3,4903),'seed':(4,123456789),
                'generate_structures':(1,0),'bonus_chest':(1,0),
                'dimensions':(10,{'minecraft:overworld':(10,{
                    'type':(8,'minecraft:overworld'),'generator':(10,generator)})})}
    write_nbt(world/'data/minecraft/world_gen_settings.dat',settings)
    write_nbt(world/'level.dat',{'Data':(10,{
        'DataVersion':(3,4903),'version':(3,19133),'LevelName':(8,'world'),
        'allowCommands':(1,1),'SpawnX':(3,0),'SpawnY':(3,-60),'SpawnZ':(3,0),
        'WorldGenSettings':(10,{'seed':(4,123456789)})})})
