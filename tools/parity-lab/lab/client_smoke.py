"""Two-server game-socket status and optional MCProtocolLib login smoke.

Run with ``python3 -m lab.client_smoke --help``. Offline scratch endpoints are
required for login; production services remain authenticated. No RCON is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

from .runner import atomic_json, interruption_signals, process_lock, utc_now
from .status import probe


def client_command(classpath_file, classes):
    entries = Path(classpath_file).read_text().strip().split(':')
    paths = [Path(classes).resolve(), *(Path(p).resolve() for p in entries)]
    if not (paths[0] / 'ClientSmoke.class').is_file() or not all(p.is_file() for p in paths[1:]):
        raise ValueError('Compile ClientSmoke and resolve its isolated dependencies first')
    return ['java', '-Xmx256m', '-XX:ActiveProcessorCount=2', '-Dio.netty.eventLoopThreads=2',
            '-cp', ':'.join(str(p) for p in paths), 'ClientSmoke'], [
        {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths[1:]]


def _compare_locked(ports, output, *, repeats=2, classpath_file=None, classes=None):
    """Internal entry: caller MUST hold process_lock through server shutdown."""
    if set(ports) != {'vanilla', 'pumpkin'} or any(type(p) is not int or not 1 <= p <= 65535 for p in ports.values()):
        raise ValueError('Specify both loopback game ports')
    if ports['vanilla'] == ports['pumpkin'] or type(repeats) is not int or not 1 <= repeats <= 3:
        raise ValueError('Distinct game ports and 1..3 repeats required')
    command, dependencies = client_command(classpath_file, classes) if classpath_file else (None, [])
    directory = Path(output) / ('client-' + uuid.uuid4().hex[:12])
    directory.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'started_at': utc_now(), 'status': 'incomplete',
              'coverage': 'status-ping-and-offline-login' if command else 'status-ping-only',
              'login_tested': False, 'gameplay_tested': False, 'shared_engine_lock_held': True,
              'expected_version': '26.3', 'expected_protocol': 777, 'results': [],
              'dependencies': dependencies,
              'client_source_sha256': hashlib.sha256(Path(__file__).with_name('client-smoke').joinpath('ClientSmoke.java').read_bytes()).hexdigest() if command else None,
              'client_class_sha256': hashlib.sha256((Path(classes) / 'ClientSmoke.class').read_bytes()).hexdigest() if command else None,
              'limitations': [
                  'No movement, inventory, block interaction, rendering or online authentication coverage.',
                  'Initial position values are recorded, not compared across independent worlds.']}
    atomic_json(directory / 'report.json', report)
    try:
        for trial in range(1, repeats + 1):
            for name in ('vanilla', 'pumpkin'):
                entry = {'target': name, 'repeat': trial, 'status': 'incomplete'}
                report['results'].append(entry)
                atomic_json(directory / 'report.json', report)
                entry['status_probe'] = probe('127.0.0.1', ports[name])
                entry['status'] = entry['status_probe']['status']
                if command and entry['status'] == 'pass':
                    report['login_tested'] = True
                    result_path = directory / f'{name}-{trial}-login.json'
                    log_path = directory / f'{name}-{trial}-client.log'
                    entry['client_log'] = log_path.name
                    with log_path.open('wb') as log:
                        try:
                            completed = subprocess.run([*command, str(ports[name]), str(result_path.resolve())],
                                                       stdout=log, stderr=subprocess.STDOUT, timeout=30)
                            entry['client_exit_code'] = completed.returncode
                            if result_path.is_file():
                                entry['login'] = json.loads(result_path.read_text())
                            entry['status'] = 'pass' if completed.returncode == 0 and entry.get('login', {}).get('status') == 'pass' else 'error'
                        except subprocess.TimeoutExpired:
                            entry.update(status='error', error='Client exceeded 30-second process deadline')
                elif command:
                    entry['login'] = {'status': 'not-run', 'reason': 'Exact-version status preflight failed'}
                atomic_json(directory / 'report.json', report)
        report['status'] = 'pass' if all(e['status'] == 'pass' for e in report['results']) else 'error'
    except BaseException as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        report['finished_at'] = utc_now()
        atomic_json(directory / 'report.json', report)
    return directory, report, 0 if report['status'] == 'pass' else 2


def compare(ports, output, **kwargs):
    with interruption_signals(), process_lock(timeout=30):
        return _compare_locked(ports, output, **kwargs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vanilla-port', type=int, required=True, help='loopback game port, never RCON')
    parser.add_argument('--pumpkin-port', type=int, required=True, help='loopback game port, never RCON')
    parser.add_argument('--output', default='artifacts/client-smoke')
    parser.add_argument('--repeat', type=int, default=2, help='1..3 bounded trials per target')
    parser.add_argument('--classpath-file', help='enables actual offline login, using MCProtocolLib 26.3')
    parser.add_argument('--classes', default='runtime/client-smoke/classes')
    args = parser.parse_args(argv)
    try:
        directory, _, code = compare({'vanilla': args.vanilla_port, 'pumpkin': args.pumpkin_port},
            args.output, repeats=args.repeat, classpath_file=args.classpath_file, classes=args.classes)
        print(directory)
        return code
    except (OSError, ValueError, KeyboardInterrupt) as exc:
        print(f'client smoke: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
