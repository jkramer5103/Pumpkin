"""Real subprocess console framing, lifecycle, and version integrity checks."""
import tempfile
import unittest
from pathlib import Path

from lab.console import ConsoleClient
from lab.rcon import RconError
from lab.runner import atomic_json
from lab.shrink import ShrinkError, load_versions


class ConsoleTests(unittest.TestCase):
    def test_console_fences_silent_commands_and_preserves_raw_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "fixture"
            binary.write_text('''#!/usr/bin/env python3
print("Server is now running", flush=True)
while True:
    command = input()
    if command == "stop": break
    if command == "silent": continue
    if command.startswith("scoreboard players get #parity_fence "):
        print("Unknown scoreboard objective '" + command.split()[-1] + "'", flush=True)
    elif command == "list": print("There are 0 of a max of 2 players online: ", flush=True)
    else: print("raw first\\nraw second", flush=True)
''')
            binary.chmod(0o700)
            client = ConsoleClient(binary, root / "scratch", timeout=1)
            try:
                client.connect()
                self.assertEqual(client.command("silent"), "")
                self.assertEqual(client.command("list"), "There are 0 of a max of 2 players online: ")
                self.assertEqual(client.command("multiline"), "raw first\nraw second")
            finally:
                client.close()
            self.assertEqual(client.process.returncode, 0)
            self.assertIn("raw first\nraw second", (root / "scratch/console.log").read_text())

    def test_console_disconnect_is_visible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "fixture"
            binary.write_text('#!/usr/bin/env python3\nprint("Server is now running", flush=True)\ninput()\n')
            binary.chmod(0o700)
            client = ConsoleClient(binary, root / "scratch", timeout=1)
            try:
                client.connect()
                with self.assertRaises(RconError):
                    client.command("crash")
            finally:
                client.close()

    def test_replay_versions_reject_changed_binary_and_arbitrary_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "binary"
            binary.write_bytes(b"initial")
            path = root / "versions.json"
            value = {"vanilla": {"version": "synthetic"}, "pumpkin": {"version": "synthetic", "binary": str(binary)}}
            atomic_json(path, value)
            verified = load_versions(path)
            atomic_json(path, verified)
            binary.write_bytes(b"changed")
            with self.assertRaisesRegex(ShrinkError, "hash differs"):
                load_versions(path)
            value["pumpkin"]["password"] = "do not copy"
            atomic_json(path, value)
            with self.assertRaisesRegex(ShrinkError, "metadata"):
                load_versions(path)


if __name__ == "__main__":
    unittest.main()
