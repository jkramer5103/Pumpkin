"""Real TCP protocol fixtures: no RCON substitute and no network dependencies."""
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from lab.status import MAX_PACKET, StatusError, frame, probe, read_varint, varint
from lab.client_smoke import compare


class GameServer:
    def __init__(self, mode='normal', protocol=777):
        self.mode, self.protocol = mode, protocol
        self.socket = socket.socket()
        self.socket.bind(('127.0.0.1', 0))
        self.port = self.socket.getsockname()[1]
        self.socket.listen()
        self.error = None
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def serve(self):
        try:
            with self.socket.accept()[0] as peer:
                peer.settimeout(2)
                def read(n):
                    data = bytearray()
                    while len(data) < n:
                        chunk = peer.recv(n-len(data))
                        if not chunk:
                            raise EOFError()
                        data.extend(chunk)
                    return bytes(data)
                def packet():
                    return read(read_varint(read))
                handshake = packet()
                # Exact 777 handshake + next-state status, not login or RCON.
                assert handshake[:3] == b'\x00\x89\x06'
                assert handshake[-1:] == b'\x01'
                assert packet() == b'\x00'
                if self.mode == 'oversize':
                    peer.sendall(varint(MAX_PACKET + 1))
                    return
                if self.mode == 'bad-varint':
                    peer.sendall(b'\x80' * 5)
                    return
                if self.mode == 'truncated':
                    peer.sendall(b'\x05\x00\x02{')
                    return
                if self.mode == 'stall':
                    time.sleep(0.12)
                    return
                raw = json.dumps({'version': {'name': '26.3', 'protocol': self.protocol},
                                  'players': {'max': 2, 'online': 0}, 'description': {'text': 'fixture'}}).encode()
                response = frame(b'\x00' + varint(len(raw)) + raw)
                # Force small socket reads / fragmented VarInts and JSON.
                for byte in response:
                    peer.sendall(bytes([byte]))
                ping = packet()
                assert len(ping) == 9 and ping[0] == 1
                if self.mode == 'wrong-pong':
                    ping = b'\x01' + struct.pack('>q', 0)
                peer.sendall(frame(ping))
        except BaseException as exc:
            self.error = exc

    def __exit__(self, *args):
        self.socket.close()
        self.thread.join(3)
        if self.thread.is_alive():
            raise AssertionError('Fixture thread failed to terminate')
        if self.error:
            raise self.error


class ClientProbeTests(unittest.TestCase):
    def test_fragmented_status_and_exact_pong(self):
        with GameServer() as server:
            result = probe('127.0.0.1', server.port)
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['pong_matches'])
        self.assertEqual(result['response']['version']['protocol'], 777)
        self.assertEqual(len(result['sent_hex']), 3)
        self.assertTrue(result['received_hex'])
        self.assertFalse(result['login_tested'])
        self.assertFalse(result['gameplay_tested'])

    def test_other_protocol_remains_incompatible_even_with_pong(self):
        with GameServer(protocol=776) as server:
            result = probe('127.0.0.1', server.port)
        self.assertEqual(result['status'], 'incompatible')
        self.assertEqual(result['response']['version']['protocol'], 776)
        self.assertTrue(result['pong_matches'])

    def test_malformed_and_truncated_frames_keep_raw_evidence(self):
        for mode in ('oversize', 'bad-varint', 'truncated', 'wrong-pong'):
            with self.subTest(mode=mode), GameServer(mode) as server:
                result = probe('127.0.0.1', server.port)
                self.assertEqual(result['status'], 'error')
                self.assertIn('error', result)
                self.assertTrue(result['received_hex'])

    def test_total_deadline(self):
        with GameServer('stall') as server:
            result = probe('127.0.0.1', server.port, timeout=0.05)
        self.assertEqual(result['status'], 'error')
        self.assertLess(result['duration_seconds'], 0.5)

    def test_validation(self):
        for host, port, timeout in [('example.com', 25565, 1), ('127.0.0.1', True, 1),
                                     ('127.0.0.1', 0, 1), ('127.0.0.1', 1, float('nan'))]:
            with self.assertRaises(StatusError):
                probe(host, port, timeout=timeout)

    def test_two_target_failure_is_preserved_and_status_is_not_login(self):
        with tempfile.TemporaryDirectory() as output, tempfile.TemporaryDirectory() as locks:
            from lab.runner import process_lock
            with GameServer() as vanilla, GameServer(protocol=776) as pumpkin:
                with patch('lab.client_smoke.process_lock', lambda **kw: process_lock(Path(locks) / 'lock')):
                    directory, report, code = compare({'vanilla': vanilla.port, 'pumpkin': pumpkin.port}, output, repeats=1)
            self.assertEqual(code, 2)
            self.assertEqual([e['status'] for e in report['results']], ['pass', 'incompatible'])
            self.assertFalse(report['login_tested'])
            self.assertEqual(report['coverage'], 'status-ping-only')
            self.assertEqual(json.loads((directory / 'report.json').read_text()), report)


if __name__ == '__main__':
    unittest.main()
