#!/usr/bin/env python3
"""Independent stdlib RCON smoke probe; never imports lab or prints credentials."""
import argparse
import json
import socket
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Rcon:
    def __init__(self, target, timeout=8):
        self.sock = socket.create_connection((target['host'], target['port']), timeout)
        self.sock.settimeout(timeout)
        self.seq = 10
        self.send(1, 3, target['password'])
        while True:
            rid, kind, _ = self.recv()
            if rid == -1:
                self.close()
                raise RuntimeError('RCON authentication rejected')
            if kind == 2 and rid == 1:
                break

    def close(self):
        self.sock.close()

    def exact(self, size):
        data = bytearray()
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError('RCON disconnected')
            data.extend(chunk)
        return bytes(data)

    def send(self, rid, kind, body):
        payload = struct.pack('<ii', rid, kind) + body.encode() + b'\0\0'
        self.sock.sendall(struct.pack('<i', len(payload)) + payload)

    def recv(self):
        size, = struct.unpack('<i', self.exact(4))
        if not 10 <= size <= 4 * 1024 * 1024:
            raise ValueError('Invalid RCON frame size')
        packet = self.exact(size)
        if packet[-2:] != b'\0\0':
            raise ValueError('Invalid RCON terminator')
        rid, kind = struct.unpack('<ii', packet[:8])
        return rid, kind, packet[8:-2].decode('utf-8', errors='replace')

    def command(self, command):
        self.seq += 2
        rid = self.seq
        self.send(rid, 2, command)
        # Read the first reply before a fence: vanilla can reject coalesced
        # command requests. TCP packet boundaries are not RCON frame boundaries.
        got, _, first = self.recv()
        if got != rid:
            raise RuntimeError('Unexpected RCON response id')
        self.send(rid + 1, 2, 'list')
        parts = [first]
        while True:
            got, _, body = self.recv()
            if got == rid + 1:
                return ''.join(parts)
            if got != rid:
                raise RuntimeError('Unexpected RCON response id')
            parts.append(body)



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, default=ROOT/'runtime/targets.json')
    parser.add_argument('--target', choices=['vanilla', 'pumpkin', 'both'], default='both')
    parser.add_argument('--command', action='append')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    targets = json.loads(args.targets.read_text())['targets']
    records = []
    for name, target in targets.items():
        if args.target not in ('both', name):
            continue
        client = Rcon(target)
        try:
            for command in args.command or ['list', 'gamerule advance_time', 'gamerule random_tick_speed']:
                records.append(dict(target=name, command=command, response=client.command(command)))
        finally:
            client.close()
    result = json.dumps(records, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result+'\n')
    print(result)

if __name__ == '__main__':
    main()
