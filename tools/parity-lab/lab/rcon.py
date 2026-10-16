"""Bounded Minecraft RCON transport with explicit response boundaries.

After reading the first reply, send a read-only `list` command using a distinct
request id. Minecraft processes these in order, so its reply marks the end of
the preceding multi-packet output. Do not coalesce requests: vanilla rejects
them. Do not use an empty command: Pumpkin emits multiple error messages for it.
The fence must be a small, complete standard player-list response. A timeout is
always an error. Auth accepts the optional Source-style empty preliminary reply.
"""

from __future__ import annotations

import socket
import struct
import time
import re


class RconError(Exception):
    """Infrastructure/transport error, not a behavioral difference."""


class AuthenticationError(RconError):
    pass


class ProtocolError(RconError):
    pass


class RconTimeout(RconError):
    pass


def packet(request_id: int, kind: int, body: str) -> bytes:
    if "\x00" in body:
        raise ValueError("RCON body cannot contain NUL")
    payload = struct.pack("<ii", request_id, kind) + body.encode("utf-8") + b"\0\0"
    return struct.pack("<i", len(payload)) + payload


class RconClient:
    max_packet_bytes = 4 * 1024 * 1024
    max_response_bytes = 16 * 1024 * 1024

    def __init__(self, host: str, port: int, password: str, *, timeout=10.0,
                 socket_factory=socket.create_connection):
        if not 0 < timeout <= 300:
            raise ValueError("timeout must be > 0 and <= 300 seconds")
        self.host, self.port = host, port
        self._password = password
        self.timeout = timeout
        self._factory = socket_factory
        self._socket = None
        self._request_id = 0
        self.last_response_packets = []
        self.last_wire_bytes = bytearray()
        self._capture_wire = False

    def _id(self):
        self._request_id = self._request_id % 2147483646 + 1
        return self._request_id

    def _remaining(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RconTimeout("RCON operation timed out")
        try:
            self._socket.settimeout(remaining)
        except OSError as exc:
            raise RconError(f"RCON socket failed ({type(exc).__name__})") from exc

    def _read_exact(self, size, deadline):
        chunks = bytearray()
        while len(chunks) < size:
            self._remaining(deadline)
            try:
                chunk = self._socket.recv(size - len(chunks))
            except (TimeoutError, socket.timeout) as exc:
                raise RconTimeout("RCON read timed out") from exc
            except OSError as exc:
                raise RconError(f"RCON read failed ({type(exc).__name__})") from exc
            if not chunk:
                raise RconError("RCON server disconnected before response boundary")
            chunks.extend(chunk)
            if self._capture_wire:
                self.last_wire_bytes.extend(chunk)
        return bytes(chunks)

    def _receive(self, deadline):
        size, = struct.unpack("<i", self._read_exact(4, deadline))
        if not 10 <= size <= self.max_packet_bytes:
            raise ProtocolError(f"Invalid RCON packet length: {size}")
        data = self._read_exact(size, deadline)
        request_id, kind = struct.unpack("<ii", data[:8])
        if data[-2:] != b"\0\0" or b"\0" in data[8:-2]:
            raise ProtocolError("Invalid RCON packet terminator/body")
        # Keep bytes until all fragments arrive; UTF-8 characters can cross packets.
        return request_id, kind, data[8:-2]

    def _send(self, data, deadline):
        self._remaining(deadline)
        try:
            self._socket.sendall(data)
        except (TimeoutError, socket.timeout) as exc:
            raise RconTimeout("RCON write timed out") from exc
        except OSError as exc:
            raise RconError(f"RCON write failed ({type(exc).__name__})") from exc

    def connect(self):
        if self._socket is not None:
            raise RconError("RCON client is already connected")
        deadline = time.monotonic() + self.timeout
        try:
            self._socket = self._factory((self.host, self.port), self.timeout)
            request_id = self._id()
            self._send(packet(request_id, 3, self._password), deadline)
            for _ in range(8):
                received_id, kind, body = self._receive(deadline)
                if received_id == -1:
                    raise AuthenticationError("RCON authentication rejected")
                if received_id != request_id:
                    raise ProtocolError("Unexpected RCON authentication request id")
                if kind == 2 and not body:
                    return self
                if kind != 0 or body:
                    raise ProtocolError("Unexpected RCON authentication packet")
            raise ProtocolError("Too many preliminary RCON authentication packets")
        except BaseException as exc:
            self.close()
            if isinstance(exc, (RconError, KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(exc, (TimeoutError, socket.timeout)):
                raise RconTimeout("RCON connection timed out") from exc
            if isinstance(exc, OSError):
                raise RconError(f"RCON connection failed ({type(exc).__name__})") from exc
            raise

    def command(self, command: str) -> str:
        self.last_response_packets = []
        self.last_wire_bytes = bytearray()
        if self._socket is None:
            raise RconError("RCON client is not connected")
        deadline = time.monotonic() + self.timeout
        request_id, boundary_id = self._id(), self._id()
        self._capture_wire = True
        try:
            self._send(packet(request_id, 2, command), deadline)
            chunks = []
            size = 0
            fence_sent = False
            for _ in range(65536):
                received_id, kind, body = self._receive(deadline)
                if kind != 0:
                    raise ProtocolError("Unexpected RCON command response type")
                if received_id == boundary_id:
                    if not chunks:
                        raise ProtocolError("RCON boundary arrived without a command response")
                    # Standard list emits one short line in this clientless lab.
                    # Reject an unsupported/oversized fence instead of leaving
                    # extra fence packets to poison the next command's stream.
                    match = re.fullmatch(rb"There are (\d+) of a max of \d+ players online: (.*)", body)
                    if not match or len(body) >= 4096:
                        raise ProtocolError("Cannot establish RCON boundary: list unavailable or oversized")
                    names = match[2].split(b", ") if match[2] else []
                    if len(names) != int(match[1]) or any(not re.fullmatch(rb"[A-Za-z0-9_]{1,16}", name) for name in names):
                        raise ProtocolError("Incomplete or nonstandard RCON list boundary")
                    try:
                        return b"".join(chunks).decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ProtocolError("RCON response is not valid UTF-8") from exc
                if received_id != request_id:
                    raise ProtocolError("Unexpected RCON command response id")
                size += len(body)
                if size > self.max_response_bytes:
                    raise ProtocolError("RCON response exceeds size limit")
                chunks.append(body)
                self.last_response_packets.append(body)
                if not fence_sent:
                    self._send(packet(boundary_id, 2, "list"), deadline)
                    fence_sent = True
            raise ProtocolError("Too many RCON response packets")
        except BaseException:
            # A broken stream must never be reused for another command.
            self.close()
            raise
        finally:
            self._capture_wire = False

    def close(self):
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *_):
        self.close()
