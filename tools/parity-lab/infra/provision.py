#!/usr/bin/env python3
"""Provision pinned official servers. Re-runs preserve worlds and passwords."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import tempfile
import tarfile
import tomllib
import urllib.request
try:
    from .rcon_probe import Rcon
    from .flat_world import seed_pumpkin_flat
except ImportError:
    from rcon_probe import Rcon
    from flat_world import seed_pumpkin_flat

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/'runtime'
MOJANG = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'
RELEASE = 'https://api.github.com/repos/Pumpkin-MC/Pumpkin/releases/latest'
PUMPKIN = '0.2.0+26.3-26.51'
SERVICES = {n: f'pumpkin-parity-{n}' for n in ('vanilla', 'pumpkin')}
RULES = {'advance_time': 'false', 'advance_weather': 'false', 'spawn_mobs': 'false',
         'random_tick_speed': '0', 'mob_griefing': 'false', 'block_drops': 'false',
         'entity_drops': 'false', 'send_command_feedback': 'true', 'log_admin_commands': 'false'}

def write(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    with os.fdopen(fd, 'w') as out:
        out.write(text)
    temporary.chmod(mode)
    temporary.replace(path)

def document(url, name):
    request = urllib.request.Request(url, headers={'User-Agent': 'Pumpkin-Parity-Lab/1'})
    raw = urllib.request.urlopen(request, timeout=60).read()
    write(RUNTIME/'upstream'/name, raw.decode())
    return raw

def digest(path, algorithm):
    with path.open('rb') as src:
        return hashlib.file_digest(src, algorithm).hexdigest()

def download(url, path, algorithm, expected):
    if not path.exists() or digest(path, algorithm) != expected:
        temp = path.with_suffix(path.suffix+'.part')
        with urllib.request.urlopen(url, timeout=90) as src, temp.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        if digest(temp, algorithm) != expected:
            temp.unlink()
            raise RuntimeError(f'Checksum mismatch: {path.name}')
        temp.replace(path)
    return {'url': url, 'path': str(path.relative_to(ROOT)), 'sha1': digest(path, 'sha1'),
            'sha256': digest(path, 'sha256'), 'bytes': path.stat().st_size}

def systemctl(action, *names):
    subprocess.run(['systemctl', action, *[SERVICES[n] for n in names]], check=True)

def unit(name):
    directory = RUNTIME/name
    command = ('/usr/bin/java -Xms256M -Xmx2G -XX:ActiveProcessorCount=2 -jar '
               f'{RUNTIME}/downloads/minecraft-26.3.jar nogui') if name == 'vanilla' else str(RUNTIME/'downloads/pumpkin-X64-Linux')
    return f'''[Unit]
Description=Pumpkin Parity Lab {name} (private loopback test server)
After=network.target
[Service]
Type=simple
WorkingDirectory={directory}
ExecStart={command}
Restart=on-failure
RestartSec=5
TimeoutStopSec=90
KillSignal=SIGTERM
MemoryMax=3G
MemorySwapMax=0
CPUQuota=150%
TasksMax=128
Environment=TOKIO_WORKER_THREADS=2 RAYON_NUM_THREADS=2
UMask=0077
NoNewPrivileges=yes
CapabilityBoundingSet=
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths={directory}
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
StandardOutput=append:{directory}/service.log
StandardError=append:{directory}/service.log
[Install]
WantedBy=multi-user.target
'''

def vanilla_config(password):
    return '\n'.join(f'{k}={v}' for k,v in {
        'server-ip':'127.0.0.1','server-port':25575,'enable-rcon':'true',
        'rcon.port':25585,'rcon.password':password,'broadcast-rcon-to-ops':'false',
        'enable-query':'false','online-mode':'true','level-name':'world',
        'level-type':'minecraft:flat','level-seed':'123456789','generate-structures':'false',
        'generator-settings':json.dumps({'biome':'minecraft:plains','layers':[
            {'block':'minecraft:bedrock','height':1},{'block':'minecraft:dirt','height':2},
            {'block':'minecraft:grass_block','height':1}], 'lakes':False,'features':False,
            'structure_overrides':[]},separators=(',',':')),
        'gamemode':'creative','difficulty':'peaceful','spawn-protection':0,'max-players':2,
        'view-distance':2,'simulation-distance':2,'pause-when-empty-seconds':0,
        'sync-chunk-writes':'true','enable-status':'true','accepts-transfers':'false',
        'management-server-enabled':'false','initial-enabled-packs':'vanilla'
    }.items())+'\n'

def pumpkin_config(password):
    # Root keys precede tables: seed/default_level_name must never become logging keys.
    value = f'''seed = "123456789"
default_level_name = "world"
default_difficulty = "Peaceful"
default_gamemode = "Creative"
allow_nether = false
allow_end = false
spawn_protection = 0
use_favicon = false
[networking.java]
enabled = true
address = "127.0.0.1:25576"
online_mode = true
view_distance = 2
simulation_distance = 2
max_players = 2
[networking.bedrock]
enabled = false
[networking.bedrock.nethernet]
enabled = false
address = "127.0.0.1:19132"
[networking.query]
enabled = false
address = "127.0.0.1:25576"
[networking.lan_broadcast]
enabled = false
[networking.rcon]
enabled = true
address = "127.0.0.1:25586"
password = "{password}"
[networking.rcon.logging]
commands = false
wrong_password = false
logged_successfully = false
quit = false
[logging]
color = false
file = "latest.log"
[commands]
use_console = false
use_tty = false
[plugins]
enabled = false
[telemetry]
enabled = false
public = false
'''
    parsed = tomllib.loads(value)
    assert parsed['networking']['rcon']['address'] == '127.0.0.1:25586'
    return value

def ready(target, seconds=180):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        try:
            return Rcon(target, timeout=3)
        except (OSError, RuntimeError, ConnectionError):
            time.sleep(2)
    raise RuntimeError('Server RCON did not become ready; inspect runtime server service.log')

def control(name, target, readiness_seconds=180):
    client = ready(target,seconds=readiness_seconds)
    records = []
    try:
        for cmd in ['list', *[f'gamerule {k} {v}' for k,v in RULES.items()],
                    'time set 6000','weather clear','setworldspawn 0 -60 0',
                    'forceload add -32 -32 32 32', 'save-all flush']:
            response = client.command(cmd)
            records.append({'command':cmd,'response':response})
        # Verify actual gamerule state on both; retain unsupported world probes as evidence.
        for key, value in RULES.items():
            cmd = f'gamerule {key}'
            response = client.command(cmd)
            records.append({'command':cmd,'response':response})
            if f'currently set to {value}' not in response:
                raise RuntimeError(f'{name} gamerule readback failed: {key}')
        # Explicit independently observed read-after-write on vanilla.
        for cmd in ['setblock 2 64 2 minecraft:stone',
                    'execute if block 2 64 2 minecraft:stone',
                    'setblock 2 64 2 minecraft:air']:
            response = client.command(cmd)
            records.append({'command':cmd,'response':response})
            if name == 'vanilla' and cmd.startswith('execute if block') and 'Test passed' not in response:
                raise RuntimeError(f'{name} failed independent block-state probe')
    finally:
        client.close()
        write(RUNTIME/f'{name}-bootstrap.json',json.dumps(records,indent=2)+'\n')
    return records

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset-worlds',action='store_true',help='Archive both worlds and create fresh worlds')
    parser.add_argument('--rotate-credentials',action='store_true',help='Explicitly replace both RCON passwords')
    args=parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    engine_lock = Path(tempfile.gettempdir())/f'pumpkin-parity-lab-{os.getuid()}.lock'
    with engine_lock.open('a') as execution, (RUNTIME/'provision.lock').open('a') as lock:
        fcntl.flock(execution,fcntl.LOCK_EX)
        fcntl.flock(lock,fcntl.LOCK_EX)
        provision(args)

def provision(args):
    previous_manifest=RUNTIME/'manifest.json'
    previous=(json.loads(previous_manifest.read_text()) if previous_manifest.exists() else {})
    (RUNTIME/'downloads').mkdir(exist_ok=True)
    metadata=json.loads(document(MOJANG,'mojang-manifest.json'))
    entry=next(v for v in metadata['versions'] if v['id']=='26.3' and v['type']=='release')
    raw=document(entry['url'],'mojang-version.json')
    if hashlib.sha1(raw).hexdigest()!=entry['sha1']:
        raise RuntimeError('Mojang version metadata checksum mismatch')
    version=json.loads(raw)
    if version['id'] != '26.3':
        raise RuntimeError('Mojang metadata has an unexpected version id')
    release=json.loads(document(RELEASE,'pumpkin-release.json'))
    if release['tag_name'] != PUMPKIN:
        raise RuntimeError(f'Official latest release changed to {release["tag_name"]}; review pin explicitly')
    tag=json.loads(document('https://api.github.com/repos/Pumpkin-MC/Pumpkin/git/ref/tags/'+PUMPKIN,'pumpkin-tag.json'))
    source_archive=RUNTIME/'downloads/pumpkin-source.tar.gz'
    if not source_archive.exists():
        request=urllib.request.Request(release['tarball_url'],headers={'User-Agent':'Pumpkin-Parity-Lab/1'})
        temporary=source_archive.with_suffix('.part')
        with urllib.request.urlopen(request,timeout=90) as src,temporary.open('wb') as dst:
            shutil.copyfileobj(src,dst)
        temporary.replace(source_archive)
    with tarfile.open(source_archive) as archive:
        prefix=archive.getmembers()[0].name
        if not prefix.endswith(tag['object']['sha'][:7]):
            raise RuntimeError('Source archive root disagrees with official tag commit')
    assets={a['name']:a for a in release['assets']}
    checks=assets['checksums.sha256']
    download(checks['browser_download_url'],RUNTIME/'downloads/checksums.sha256','sha256',checks['digest'].removeprefix('sha256:'))
    expected=next(line.split()[0] for line in (RUNTIME/'downloads/checksums.sha256').read_text().splitlines() if line.split()[-1].lstrip('*')=='pumpkin-X64-Linux')
    asset=assets['pumpkin-X64-Linux']
    if asset['digest'] != 'sha256:'+expected:
        raise RuntimeError('Release digest disagrees with checksum file')
    pumpkin=download(asset['browser_download_url'],RUNTIME/'downloads/pumpkin-X64-Linux','sha256',expected)
    (RUNTIME/'downloads/pumpkin-X64-Linux').chmod(0o755)
    server=version['downloads']['server']
    vanilla=download(server['url'],RUNTIME/'downloads/minecraft-26.3.jar','sha1',server['sha1'])
    target_path=RUNTIME/'targets.json'
    if target_path.exists():
        targets=json.loads(target_path.read_text())
        if targets.get('minecraft_version')!='26.3' or set(targets['targets'])!={'vanilla','pumpkin'}:
            raise RuntimeError('Existing targets do not match contract')
    else:
        targets={'schema_version':1,'minecraft_version':'26.3','targets':{}}
    for name,port in [('vanilla',25585),('pumpkin',25586)]:
        old=targets['targets'].get(name,{})
        targets['targets'][name]={'host':'127.0.0.1','port':port,'password':old.get('password') if old.get('password') and not args.rotate_credentials else secrets.token_hex(24)}
    # Stop only our two units before changing config or archiving worlds.
    for name in SERVICES:
        if Path('/etc/systemd/system/'+SERVICES[name]+'.service').exists():
            systemctl('stop',name)
    if args.reset_worlds:
        stamp=datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%SZ')
        for name in SERVICES:
            world=RUNTIME/name/'world'
            if world.exists():
                world.rename(world.with_name('world.archive-'+stamp))
    write(target_path,json.dumps(targets,indent=2)+'\n')
    for name in SERVICES:
        (RUNTIME/name).mkdir(exist_ok=True)
        write(Path('/etc/systemd/system')/(SERVICES[name]+'.service'),unit(name),0o644)
    write(RUNTIME/'vanilla/eula.txt','# Accepted for user-authorized private parity test setup.\neula=true\n')
    write(RUNTIME/'vanilla/server.properties',vanilla_config(targets['targets']['vanilla']['password']))
    write(RUNTIME/'pumpkin/pumpkin.toml',pumpkin_config(targets['targets']['pumpkin']['password']))
    systemctl('daemon-reload')
    systemctl('enable','vanilla','pumpkin')
    systemctl('start','vanilla')
    control('vanilla',targets['targets']['vanilla'])
    # Tagged release reads flat generator settings from the split world data file.
    # Seed independent empty metadata at Pumpkin's supported DataVersion (4903).
    world=RUNTIME/'pumpkin/world'
    if not (world/'level.dat').exists():
        seed_pumpkin_flat(world)
    systemctl('start','pumpkin')
    control('pumpkin',targets['targets']['pumpkin'])
    config=tomllib.loads((RUNTIME/'pumpkin/pumpkin.toml').read_text())
    if config['networking']['java']['address']!='127.0.0.1:25576' or config['networking']['rcon']['address']!='127.0.0.1:25586':
        raise RuntimeError('Generated Pumpkin bindings disagree with contract')
    write(RUNTIME/'manifest.json',json.dumps({
        **{k:previous[k] for k in ('active_candidate','source_baseline_attempts') if k in previous},
        'schema_version':1,'provisioned_at':datetime.datetime.now(datetime.UTC).isoformat(),
        'minecraft_version':'26.3','pumpkin_version':PUMPKIN,
        'mojang_manifest_url':MOJANG,'mojang_version_url':entry['url'],
        'mojang_version_sha1':entry['sha1'],'pumpkin_release_api':RELEASE,
        'pumpkin_release_url':release['html_url'],'pumpkin_release_published_at':release['published_at'],
        'pumpkin_source_tag_commit':tag['object']['sha'],
        'pumpkin_source_url':release['tarball_url'],
        'pumpkin_source_archive_sha256':digest(RUNTIME/'downloads/pumpkin-source.tar.gz','sha256') if (RUNTIME/'downloads/pumpkin-source.tar.gz').exists() else None,
        'pumpkin_source_files_read':['crates/pumpkin-config/src/lib.rs','crates/pumpkin-config/src/networking/rcon.rs','crates/pumpkin-world/src/world_info/anvil.rs','crates/pumpkin-world/src/world_info/data_files.rs','crates/pumpkin-world/src/level.rs'],
        'pumpkin_checksum_url':checks['browser_download_url'],'pumpkin_checksum_sha256':checks['digest'],
        'binaries':{'vanilla':vanilla,'pumpkin':pumpkin},'gamerules_requested':RULES,
        'world_initialization':'independent fresh flat metadata; Pumpkin seed uses its supported DataVersion 4903 and split world_gen_settings.dat; no chunks copied',
        'eula_accepted':True,'ports':{'vanilla':{'game':25575,'rcon':25585},'pumpkin':{'game':25576,'rcon':25586}},
        'bind':'127.0.0.1','resources':{'MemoryMax':'3G','CPUQuota':'150%','TasksMax':128},
        'docs':['https://docs.pumpkinmc.org/config/basic','https://docs.pumpkinmc.org/config/rcon'],
        },indent=2)+'\n',0o644)
    print('Both official servers booted; independent RCON and gamerule readbacks passed. World probe limitations are retained in bootstrap evidence. Manifest: runtime/manifest.json')

if __name__=='__main__':
    main()
