"""Bounded Java status request and ping on the game socket; never opens RCON."""
from __future__ import annotations

import io
import json
import math
import socket
import struct
import time

PROTOCOL = 777
VERSION = '26.3'
MAX_PACKET = 1024 * 1024


class StatusError(ValueError):
    pass


def varint(value):
    if type(value) is not int or not 0 <= value <= 0x7fffffff:
        raise StatusError('Expected a nonnegative signed VarInt')
    data = bytearray()
    while value > 127:
        data.append((value & 127) | 128)
        value >>= 7
    return bytes(data + bytes([value]))


def read_varint(read):
    value = 0
    for index in range(5):
        byte = read(1)[0]
        value |= (byte & 127) << (7 * index)
        if not byte & 128:
            if value > 0x7fffffff:
                raise StatusError('Negative or overflowing VarInt')
            return value
    raise StatusError('VarInt exceeds five bytes')


def frame(payload):
    return varint(len(payload)) + payload


def probe(host, port, *, timeout=5):
    """Return raw request/response evidence, including failures; one total deadline."""
    if host != '127.0.0.1' or type(port) is not int or not 1 <= port <= 65535:
        raise StatusError('Only explicit IPv4 loopback game ports are allowed')
    if not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise StatusError('Timeout must be finite, positive and <=30 seconds')
    evidence = {'host': host, 'port': port, 'requested_protocol': PROTOCOL,
                'status': 'error', 'sent_hex': [], 'received_hex': '',
                'coverage': 'status-ping-only', 'login_tested': False, 'gameplay_tested': False}
    received = bytearray()
    deadline = time.monotonic() + timeout
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            def read(size):
                data = bytearray()
                while len(data) < size:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Status probe deadline expired')
                    sock.settimeout(remaining)
                    chunk = sock.recv(size - len(data))
                    if not chunk:
                        raise StatusError('Game socket closed before the packet completed')
                    received.extend(chunk)
                    data.extend(chunk)
                return bytes(data)

            def packet():
                length = read_varint(read)
                if not 1 <= length <= MAX_PACKET:
                    raise StatusError('Invalid or oversized status packet')
                return read(length)

            def send(payload):
                wire = frame(payload)
                evidence['sent_hex'].append(wire.hex())
                sock.settimeout(max(0.001, deadline - time.monotonic()))
                sock.sendall(wire)

            hostname = host.encode('utf-8')
            send(b'\x00' + varint(PROTOCOL) + varint(len(hostname)) + hostname + struct.pack('>H', port) + b'\x01')
            send(b'\x00')
            payload = io.BytesIO(packet())
            def body_read(size):
                value = payload.read(size)
                if len(value) != size:
                    raise StatusError('Truncated status JSON field')
                return value
            if read_varint(body_read) != 0:
                raise StatusError('Unexpected status response packet ID')
            length = read_varint(body_read)
            if length > MAX_PACKET:
                raise StatusError('Oversized status JSON field')
            raw = body_read(length).decode('utf-8')
            evidence['raw_status_json'] = raw
            if payload.read(1):
                raise StatusError('Trailing status response data')
            status = json.loads(raw)
            evidence['response'] = status
            token = struct.pack('>q', time.monotonic_ns())
            ping_started = time.monotonic()
            send(b'\x01' + token)
            if packet() != b'\x01' + token:
                raise StatusError('Pong did not echo the exact signed long payload')
            evidence['pong_matches'] = True
            evidence['latency_ms'] = (time.monotonic() - ping_started) * 1000
            if (not isinstance(status, dict) or not isinstance(status.get('version'), dict)
                    or type(status['version'].get('protocol')) is not int
                    or not isinstance(status['version'].get('name'), str)):
                raise StatusError('Status is missing a valid version name/protocol')
            evidence['status'] = 'pass' if status['version']['name'] == VERSION and status['version']['protocol'] == PROTOCOL else 'incompatible'
    except (OSError, ValueError, IndexError) as exc:
        evidence['error'] = f'{type(exc).__name__}: {exc}'
    evidence['received_hex'] = received.hex()
    evidence['duration_seconds'] = time.monotonic() - started
    return evidence
