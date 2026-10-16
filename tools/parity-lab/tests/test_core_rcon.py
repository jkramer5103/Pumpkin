import socket
import struct
import unittest

from lab.rcon import AuthenticationError, ProtocolError, RconClient, RconError, RconTimeout, packet


class FakeSocket:
    """recv obeys requested size, but splits traffic at arbitrary TCP boundaries."""

    def __init__(self, incoming, fragment=1):
        self.incoming = bytearray(incoming)
        self.fragment = fragment
        self.sent = []
        self.closed = False
        self.timeouts = []

    def settimeout(self, seconds):
        self.timeouts.append(seconds)

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        take = min(size, self.fragment, len(self.incoming))
        result = bytes(self.incoming[:take])
        del self.incoming[:take]
        return result

    def close(self):
        self.closed = True


def client_for(incoming, fragment=1, socket_type=FakeSocket):
    sock = socket_type(incoming, fragment)
    return RconClient("127.0.0.1", 25585, "secret-never-log", timeout=0.2,
                      socket_factory=lambda address, timeout: sock), sock


class RconTests(unittest.TestCase):
    def test_fragmented_auth_and_multi_packet_response(self):
        wire = packet(1, 0, "") + packet(1, 2, "")
        wire += packet(2, 0, "first\n") + packet(2, 0, "second") + packet(3, 0, "There are 0 of a max of 2 players online: ")
        for fragment in (1, 2, 3, 7, 4096):
            with self.subTest(fragment=fragment):
                client, sock = client_for(wire, fragment)
                with client:
                    self.assertEqual(client.command("list"), "first\nsecond")
                self.assertTrue(sock.closed)
                self.assertEqual(sock.sent[0], packet(1, 3, "secret-never-log"))
                self.assertEqual(sock.sent[1], packet(2, 2, "list"))
                self.assertEqual(sock.sent[2], packet(3, 2, "list"))
                self.assertTrue(all(0 < timeout <= 0.2 for timeout in sock.timeouts))

    def test_auth_without_preliminary_response(self):
        client, _ = client_for(packet(1, 2, ""))
        with client:
            pass

    def test_auth_rejected_and_password_not_exposed(self):
        client, sock = client_for(packet(1, 0, "") + packet(-1, 2, ""))
        with self.assertRaises(AuthenticationError) as caught:
            client.connect()
        self.assertNotIn("secret-never-log", str(caught.exception))
        self.assertTrue(sock.closed)

    def test_auth_unexpected_packet(self):
        for wire in (packet(9, 2, ""), packet(1, 0, "not empty"), packet(1, 4, ""), packet(1, 2, "unexpected body")):
            client, sock = client_for(wire)
            with self.assertRaises(ProtocolError):
                client.connect()
            self.assertTrue(sock.closed)

    def test_empty_response_is_complete_and_valid(self):
        client, _ = client_for(packet(1, 2, "") + packet(2, 0, "") + packet(3, 0, "There are 0 of a max of 2 players online: "))
        with client:
            self.assertEqual(client.command("execute if block 0 64 0 stone"), "")

    def test_multiple_commands_do_not_consume_next_response(self):
        wire = packet(1, 2, "") + packet(2, 0, "one") + packet(3, 0, "There are 0 of a max of 2 players online: ")
        wire += packet(4, 0, "two") + packet(5, 0, "There are 0 of a max of 2 players online: ")
        client, _ = client_for(wire, 4096)
        with client:
            self.assertEqual(client.command("first"), "one")
            self.assertEqual(client.command("second"), "two")

    def test_utf8_split_across_response_packets(self):
        def byte_packet(request_id, body):
            return struct.pack("<iii", len(body) + 10, request_id, 0) + body + b"\0\0"
        wire = packet(1, 2, "") + byte_packet(2, b"\xe2") + byte_packet(2, b"\x98\x83") + packet(3, 0, "There are 0 of a max of 2 players online: ")
        client, _ = client_for(wire)
        with client:
            self.assertEqual(client.command("snow"), "☃")

    def test_disconnect_in_header_body_and_before_boundary_is_error(self):
        auth = packet(1, 2, "")
        for response in (b"\x10", packet(2, 0, "hello")[:-3], packet(2, 0, "partial")):
            client, sock = client_for(auth + response)
            client.connect()
            with self.assertRaises(RconError):
                client.command("test")
            self.assertTrue(sock.closed)

    def test_read_timeout_is_never_an_output_boundary(self):
        class TimeoutSocket(FakeSocket):
            def recv(self, size):
                if not self.incoming:
                    raise socket.timeout()
                return super().recv(size)
        client, sock = client_for(packet(1, 2, "") + packet(2, 0, "partial"), socket_type=TimeoutSocket)
        client.connect()
        with self.assertRaises(RconTimeout):
            client.command("test")
        self.assertTrue(sock.closed)
        self.assertEqual(client.last_response_packets, [b"partial"])
        self.assertEqual(bytes(client.last_wire_bytes), packet(2, 0, "partial"))
        self.assertNotIn(b"secret-never-log", client.last_wire_bytes)

    def test_fence_is_sent_after_first_response_is_read(self):
        class SequentialSocket(FakeSocket):
            def sendall(self, data):
                if len(self.sent) == 2:
                    self.assert_first_read()
                super().sendall(data)

            def assert_first_read(self):
                # Auth and the complete first output packet have been read.
                if self.incoming != bytearray(packet(3, 0, "There are 0 of a max of 2 players online: ")):
                    raise AssertionError("Fence was sent before the first command reply")
        client, _ = client_for(packet(1, 2, "") + packet(2, 0, "first") + packet(3, 0, "There are 0 of a max of 2 players online: "), socket_type=SequentialSocket)
        with client:
            self.assertEqual(client.command("probe"), "first")

    def test_incomplete_unsupported_or_oversized_fence_is_error(self):
        for raw in ("Unknown command", "There are 2 of a max of 2 players online: one",
                    "There are 0 of a max of 2 players online: extra",
                    "There are 1 of a max of 2 players online: " + "x" * 4096):
            client, _ = client_for(packet(1, 2, "") + packet(2, 0, "output") + packet(3, 0, raw))
            with client:
                with self.assertRaises(ProtocolError):
                    client.command("probe")

    def test_auth_timeout(self):
        class TimeoutSocket(FakeSocket):
            def recv(self, size):
                raise socket.timeout()
        client, sock = client_for(b"", socket_type=TimeoutSocket)
        with self.assertRaises(RconTimeout):
            client.connect()
        self.assertTrue(sock.closed)

    def test_malformed_frames_and_wrong_ids(self):
        responses = [struct.pack("<i", -1), struct.pack("<i", 9), struct.pack("<i", 99999999),
                     packet(2, 0, "hello")[:-1] + b"x", packet(2, 2, "wrong type"),
                     packet(100, 0, "wrong id"), packet(3, 0, "no command response"),
                     struct.pack("<iii", 11, 2, 0) + b"\xff\0\0" + packet(3, 0, "There are 0 of a max of 2 players online: ")]
        for response in responses:
            with self.subTest(response=response):
                client, sock = client_for(packet(1, 2, "") + response)
                client.connect()
                with self.assertRaises(ProtocolError):
                    client.command("test")
                self.assertTrue(sock.closed)

    def test_response_memory_bound(self):
        client, _ = client_for(packet(1, 2, "") + packet(2, 0, "abc") + packet(2, 0, "def"))
        client.max_response_bytes = 5
        with client:
            with self.assertRaises(ProtocolError):
                client.command("test")

    def test_connection_failure_has_safe_message(self):
        def fail(address, timeout):
            raise ConnectionRefusedError("secret-never-log")
        client = RconClient("127.0.0.1", 1, "secret-never-log", socket_factory=fail)
        with self.assertRaises(RconError) as caught:
            client.connect()
        self.assertNotIn("secret-never-log", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
