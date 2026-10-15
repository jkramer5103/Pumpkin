"""Explicit scratch-console transport for upstream builds without RCON.

This is never selected automatically and does not imply RCON support. The caller
must create/connect/close it under the engine lock. Full stdout is retained.
"""
from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import threading
import time

from .rcon import RconError


CONFIG = '''allow_nether = false
allow_end = false
[networking.java]
enabled = true
address = "127.0.0.1:0"
online_mode = false
encryption = false
max_players = 2
view_distance = 2
simulation_distance = 2
[networking.bedrock]
enabled = false
[networking.query]
enabled = false
[networking.management]
enabled = false
[networking.lan_broadcast]
enabled = false
[commands]
use_console = true
use_tty = false
broadcast_console_to_ops = false
[plugins]
enabled = false
[telemetry]
enabled = false
'''


class ConsoleClient:
    def __init__(self, binary, directory, *, timeout=10):
        self.binary = Path(binary).resolve()
        self.directory = Path(directory)
        self.timeout = timeout
        self.process = None
        self.log = None
        self.reader = None
        self.lines = queue.Queue()

    def connect(self):
        self.directory.mkdir(parents=True, exist_ok=False)
        (self.directory / 'pumpkin.toml').write_text(CONFIG)
        self.log = (self.directory / 'console.log').open('x', encoding='utf-8')
        try:
            self.process = subprocess.Popen([str(self.binary)], cwd=self.directory,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                env={**os.environ, 'NO_COLOR': '1', 'RAYON_NUM_THREADS': '2', 'TOKIO_WORKER_THREADS': '2'})

            def read():
                try:
                    for line in self.process.stdout:
                        self.log.write(line)
                        self.log.flush()
                        self.lines.put(line.rstrip('\n'))
                finally:
                    self.lines.put(None)

            self.reader = threading.Thread(target=read, daemon=True)
            self.reader.start()
            deadline = time.monotonic() + max(20, self.timeout)
            while 'Server is now running' not in self._receive(deadline):
                pass
        except (OSError, RconError):
            self.close()
            raise

    def _receive(self, deadline):
        try:
            line = self.lines.get(timeout=max(0.001, deadline - time.monotonic()))
        except queue.Empty as exc:
            raise RconError('Timed out waiting for scratch console output') from exc
        if line is None:
            raise RconError('Scratch console closed its output')
        return line

    def command(self, command):
        try:
            # A read-only list fence follows every command, including silent
            # conditions. Raw console lines before the fence are not normalized.
            self.process.stdin.write(command + '\nlist\n')
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise RconError('Could not write scratch console command') from exc
        deadline = time.monotonic() + self.timeout
        output = []
        while True:
            line = self._receive(deadline)
            if line.startswith('There are 0 of a max of 2 players online:'):
                return '\n'.join(output)
            output.append(line)

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    self.process.stdin.write('stop\n')
                    self.process.stdin.flush()
                    self.process.wait(timeout=8)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    self.process.kill()
                    self.process.wait(timeout=3)
            if self.reader:
                self.reader.join(3)
            for stream in (self.process.stdin, self.process.stdout):
                stream.close()
        if self.log is not None:
            self.log.close()
