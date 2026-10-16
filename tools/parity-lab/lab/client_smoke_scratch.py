"""Boot private offline scratch servers and run the actual two-server client harness.

Use only lab binaries. Run inside a resource-capped systemd scope (see lab/client-smoke/README.md).
All startup, login and shutdown happen under the same engine process lock.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
from pathlib import Path
import os
import socket
import subprocess
import sys
import threading
import time
import uuid

from .arena import seed_arena
from .client_smoke import _compare_locked
from .console import CONFIG
from .runner import atomic_json, interruption_signals, process_lock, utc_now
from .status import probe


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def server(name, binary, directory, record, save):
    """Caller holds engine lock. No live-service config or world is used."""
    directory.mkdir()
    port = free_port()
    if name == 'vanilla':
        (directory / 'eula.txt').write_text('eula=true\n')
        (directory / 'server.properties').write_text('\n'.join([
            'server-ip=127.0.0.1', f'server-port={port}', 'online-mode=false',
            'white-list=false', 'enforce-whitelist=false', 'enforce-secure-profile=false',
            'enable-rcon=false', 'enable-query=false', 'level-type=minecraft:flat',
            'generator-settings={"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains","features":false,"lakes":false,"structure_overrides":[]}',
            'view-distance=2', 'simulation-distance=2', 'max-players=2', 'gamemode=creative',
            'difficulty=peaceful', 'spawn-protection=0', 'sync-chunk-writes=false',
            'pause-when-empty-seconds=0', 'level-seed=1']) + '\n')
        command = ['java', '-Xms128M', '-Xmx768M', '-XX:ActiveProcessorCount=2', '-jar', str(binary), 'nogui']
        ready = 'Done ('
        spawn = 'setworldspawn 0 -60 0'
    else:
        seed_arena(directory)
        (directory / 'pumpkin.toml').write_text('default_difficulty = "Peaceful"\ndefault_gamemode = "Creative"\n' + CONFIG.replace('127.0.0.1:0', f'127.0.0.1:{port}'))
        command, ready = [str(binary)], 'Server is now running'
        spawn = 'setworldspawn 0 64 0'
    evidence = {'binary': str(binary), 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                'port': port, 'command': command, 'ready': False, 'stopped': False,
                'bootstrap_status_probes': [], 'setup_console_command': spawn}
    record['servers'][name] = evidence
    save()
    with (directory / 'console.log').open('w') as log:
        process = subprocess.Popen(command, cwd=directory, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
            env={**os.environ, 'NO_COLOR': '1', 'RAYON_NUM_THREADS': '2', 'TOKIO_WORKER_THREADS': '2'})
        def read():
            for line in process.stdout:
                log.write(line)
                log.flush()
                if ready in line:
                    evidence['ready'] = True
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            deadline = time.monotonic() + 80
            while not evidence['ready'] and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.1)
            if not evidence['ready']:
                raise RuntimeError(name + ' startup failed; inspect console.log')
            process.stdin.write(spawn + '\n')
            process.stdin.flush()
            # Vanilla's initial status cache can lag its Done log. Bootstrap is
            # recorded separately; measured trials never silently retry failures.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                result = probe('127.0.0.1', port, timeout=2)
                evidence['bootstrap_status_probes'].append(result)
                save()
                if result['status'] == 'pass':
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(name + ' exact-version status readiness failed')
            yield port
        finally:
            if process.poll() is None:
                try:
                    process.stdin.write('stop\n')
                    process.stdin.flush()
                    process.wait(timeout=20)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait(timeout=5)
                    evidence['forced_stop'] = True
            reader.join(3)
            for stream in (process.stdin, process.stdout):
                stream.close()
            evidence.update(stopped=True, server_exit_code=process.returncode)
            save()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vanilla-jar', type=Path, required=True)
    parser.add_argument('--pumpkin-binary', type=Path, required=True)
    parser.add_argument('--pumpkin-source', required=True, help='declared source revision; binary SHA-256 is recorded')
    parser.add_argument('--classpath-file', type=Path, default=Path('runtime/client-smoke/classpath.txt'))
    parser.add_argument('--classes', type=Path, default=Path('runtime/client-smoke/classes'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/client-smoke-scratch'))
    parser.add_argument('--repeat', type=int, choices=(1, 2, 3), default=2)
    args = parser.parse_args(argv)
    directory = args.output.resolve() / ('scratch-' + uuid.uuid4().hex[:12])
    directory.mkdir(parents=True, exist_ok=False)
    record = {'started_at': utc_now(), 'status': 'incomplete', 'servers': {},
              'declared_pumpkin_source': args.pumpkin_source, 'shared_engine_lock_held': False,
              'gameplay_tested': False, 'live_services_modified': False}
    def save():
        atomic_json(directory / 'validation.json', record)
    save()
    code = 2
    try:
        with interruption_signals(), process_lock(timeout=30):
            record['shared_engine_lock_held'] = True
            with server('vanilla', args.vanilla_jar.resolve(), directory / 'vanilla', record, save) as vanilla:
                with server('pumpkin', args.pumpkin_binary.resolve(), directory / 'pumpkin', record, save) as pumpkin:
                    run_dir, report, code = _compare_locked({'vanilla': vanilla, 'pumpkin': pumpkin}, directory / 'runs',
                        repeats=args.repeat, classpath_file=args.classpath_file, classes=args.classes)
                    record.update(status=report['status'], report=str(run_dir / 'report.json'))
            if any(s.get('forced_stop') or s.get('server_exit_code') != 0 for s in record['servers'].values()):
                record['status'], code = 'error', 2
    except (OSError, ValueError, RuntimeError, KeyboardInterrupt) as exc:
        record.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finally:
        record['finished_at'] = utc_now()
        save()
        print(directory, flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
