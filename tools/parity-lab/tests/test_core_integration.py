"""End-to-end tests against two local TCP RCON fixtures, never real services."""

import contextlib
import json
import os
import signal
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path

from lab.rcon import packet
from lab.runner import atomic_json, run
from lab.shrink import replay_reproducer, shrink_scenario


class FixtureServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, name, mode="different"):
        self.name = name
        self.mode = mode
        self.commands = []
        self.probe_requested = threading.Event()
        self.release_probe = threading.Event()
        self.created = False
        self.triggered = False
        super().__init__(("127.0.0.1", 0), FixtureHandler)

    def response(self, command):
        self.commands.append(command)
        if command == "list":
            return ["There are 0 of a max of 2 players online: "]
        if command == "reset":
            self.created, self.triggered = False, False
        if command == "create":
            self.created = True
        if command == "trigger":
            self.triggered = True
        if command == "probe":
            self.probe_requested.set()
            if self.mode == "hang":
                self.release_probe.wait(3)
            if self.mode == "unsupported":
                return ["Unknown or incomplete command, see below for error", "probe<--[HERE]"]
            if not self.created or not self.triggered:
                return [""]
            raw = "PARITY:ready"
            if self.name == "pumpkin" and self.mode == "different":
                raw += " divergent"
            # Several output frames and sender wrappers exercise the full path.
            return [("[Rcon] " if self.name == "vanilla" else "[Server] ") + raw[:7], raw[7:]]
        return ["OK"]


class FixtureHandler(socketserver.BaseRequestHandler):
    def exact(self, size):
        data = bytearray()
        while len(data) < size:
            chunk = self.request.recv(size - len(data))
            if not chunk:
                raise EOFError()
            data.extend(chunk)
        return bytes(data)

    def send(self, data):
        # Deliberately fragment the wire, including packet headers and bodies.
        for start in range(0, len(data), 3):
            self.request.sendall(data[start:start + 3])

    def handle(self):
        self.request.settimeout(5)
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        authenticated = False
        try:
            while True:
                size, = struct.unpack("<i", self.exact(4))
                data = self.exact(size)
                request_id, kind = struct.unpack("<ii", data[:8])
                body = data[8:-2].decode()
                if kind == 3:
                    authenticated = body == "fixture-only"
                    self.send(packet(request_id, 0, "") + packet(request_id if authenticated else -1, 2, ""))
                elif kind == 2 and authenticated:
                    for response in self.server.response(body):
                        self.send(packet(request_id, 0, response))
                else:
                    return
        except (EOFError, OSError):
            return


@contextlib.contextmanager
def fixture_pair(mode="different"):
    servers = [FixtureServer(name, mode) for name in ("vanilla", "pumpkin")]
    threads = [threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
               for server in servers]
    for thread in threads:
        thread.start()
    try:
        config = {"schema_version": 1, "minecraft_version": "fixture", "targets": {
            server.name: {"host": "127.0.0.1", "port": server.server_address[1], "password": "fixture-only"}
            for server in servers}}
        yield servers, config
    finally:
        for server in servers:
            server.release_probe.set()
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(1)


def fixture_scenario():
    return {"schema_version": 1, "id": "synthetic-state", "title": "Synthetic state", "category": "fixture",
            "description": "TCP test fixture, not Minecraft coverage", "tags": ["fixture"],
            "setup": ["reset"], "cleanup": ["reset"],
            "steps": [{"command": command, **({"observe": True, "expect_contains": "PARITY:ready"}
                       if command == "probe" else {})}
                      for command in ("noise-a", "create", "noise-b", "trigger", "probe", "noise-c")]}


def shrink_inputs(root):
    atomic_json(root / "reset.json", {"commands": ["reset"]})
    atomic_json(root / "versions.json", {name: {"version": "synthetic TCP fixture", "transport": "rcon"}
                                        for name in ("vanilla", "pumpkin")})
    return {"reset_path": root / "reset.json", "versions_path": root / "versions.json"}


class TcpIntegrationTests(unittest.TestCase):
    def setUp(self):
        # These endpoints are synthetic. Give parent and CLI subprocesses the
        # same private lock so a live catalog run cannot stall fixture tests.
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(mock.patch.object(tempfile, "tempdir", temporary))
        self.enterContext(mock.patch.dict(os.environ, {"TMPDIR": temporary}))

    def test_full_runner_over_fragmented_tcp_responses(self):
        with tempfile.TemporaryDirectory() as temporary, fixture_pair() as (servers, targets):
            directory, report, code = run([fixture_scenario()], targets, temporary, repeat=2, timeout=2)
            self.assertEqual(code, 1)
            self.assertTrue(report["results"][0]["confirmed_mismatch"])
            for server in servers:
                self.assertEqual(server.commands.count("probe"), 2)
            for name in ("vanilla", "pumpkin"):
                transcript = directory / "transcripts" / (name + ".jsonl")
                records = [json.loads(line) for line in transcript.read_text().splitlines()]
                probe = next(e for e in records if e.get("command") == "probe" and e["event"] == "response")
                self.assertEqual(len(probe["response_packets_hex"]), 2)
                self.assertEqual(b"".join(bytes.fromhex(s) for s in probe["response_packets_hex"]).decode(), probe["raw"])

    def test_cli_pass_and_difference_exit_codes(self):
        for mode, expected in (("pass", 0), ("different", 1), ("unsupported", 1)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary, fixture_pair(mode) as (_, targets):
                root = Path(temporary)
                cases = root / "scenarios"
                cases.mkdir()
                atomic_json(cases / "case.json", fixture_scenario())
                atomic_json(root / "targets.json", targets)
                result = subprocess.run([sys.executable, "-m", "lab", "run", "--targets", str(root / "targets.json"),
                    "--scenarios", str(cases), "--output", str(root / "runs"), "--repeat", "2", "--timeout", "2"],
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stderr)
                report = json.loads((Path(result.stdout.strip()) / "report.json").read_text())
                self.assertTrue(report["complete"])
                self.assertNotIn("fixture-only", (Path(result.stdout.strip()) / "report.json").read_text())

    def test_scenario_shrinking_reexecutes_both_servers_and_final_reproducer(self):
        with tempfile.TemporaryDirectory() as temporary, fixture_pair() as (servers, targets):
            root = Path(temporary)
            atomic_json(root / "case.json", fixture_scenario())
            atomic_json(root / "targets.json", targets)
            directory, report, code = shrink_scenario(root / "case.json", root / "targets.json", root / "shrinks", timeout=2, **shrink_inputs(root))
            self.assertEqual(code, 0, report)
            self.assertTrue(report["minimized"])
            self.assertEqual(report["retained_indices"], [1, 3, 4])
            reproducer = json.loads((directory / "reproducer.json").read_text())
            self.assertEqual([s["command"] for s in reproducer["steps"]], ["create", "trigger", "probe"])
            self.assertEqual(report["probes"][-1]["indices"], report["retained_indices"])
            self.assertEqual(report["verified_run"], report["probes"][-1]["run"])
            final = json.loads((Path(report["verified_run"]) / "report.json").read_text())
            self.assertTrue(final["results"][0]["confirmed_mismatch"])
            self.assertGreater(len(report["probes"]), 3)
            for server in servers:
                self.assertEqual(server.commands.count("probe"), 2 * len(report["probes"]))

    def test_shrink_cli_pins_observations_resets_every_attempt_and_replays(self):
        with tempfile.TemporaryDirectory() as temporary, fixture_pair() as (servers, targets):
            root = Path(temporary)
            case = fixture_scenario()
            # Even an observation irrelevant to the mismatch must remain.
            case["steps"].insert(1, {"command": "observe-always", "observe": True, "expect_contains": "OK"})
            # Required setup is independent of the explicitly recorded reset.
            case["setup"] = ["prepare"]
            atomic_json(root / "case.json", case)
            atomic_json(root / "targets.json", targets)
            shrink_inputs(root)
            result = subprocess.run([sys.executable, "-m", "lab", "shrink",
                "--scenario", str(root / "case.json"), "--targets", str(root / "targets.json"),
                "--reset", str(root / "reset.json"), "--versions", str(root / "versions.json"),
                "--keep-step", "0", "--output", str(root / "reproducers"), "--timeout", "2"],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            directory = Path(result.stdout.strip())
            report = json.loads((directory / "shrink-report.json").read_text())
            reduced = json.loads((directory / "reproducer.json").read_text())
            self.assertEqual([s["command"] for s in reduced["steps"]],
                             ["noise-a", "observe-always", "create", "trigger", "probe"])
            self.assertEqual(reduced["setup"], ["prepare"])
            self.assertEqual(report["pinned_indices"], [0, 1, 5])
            self.assertIn("synthetic", report["target_versions"]["pumpkin"]["version"])
            self.assertEqual(json.loads((directory / "attempts.json").read_text()), report["probes"])
            # Every removable single deletion was actually rerun on both TCP servers.
            for index in set(report["retained_indices"]) - set(report["pinned_indices"]):
                deletion = [i for i in report["retained_indices"] if i != index]
                self.assertTrue(any(p["indices"] == deletion and not p["accepted"] for p in report["probes"]))
            replay = subprocess.run(report["replay_argv"], capture_output=True, text=True, timeout=10)
            self.assertEqual(replay.returncode, 1, replay.stderr)
            replay_report = json.loads((Path(replay.stdout.strip()) / "report.json").read_text())
            self.assertTrue(replay_report["results"][0]["confirmed_mismatch"])
            for server in servers:
                self.assertEqual(server.commands.count("prepare"), 2 * (len(report["probes"]) + 1))
                # Mutating setup is always immediately preceded by an arena reset
                # (and the RCON read-only fence).
                for index, command in enumerate(server.commands):
                    if command == "prepare":
                        self.assertEqual(server.commands[index-2:index], ["reset", "list"])
            self.assertNotIn("fixture-only", (directory / "shrink-report.json").read_text())

    def test_budget_exhaustion_retains_best_verified_candidate_without_minimality(self):
        with tempfile.TemporaryDirectory() as temporary, fixture_pair() as (_, targets):
            root = Path(temporary)
            atomic_json(root / "case.json", fixture_scenario())
            atomic_json(root / "targets.json", targets)
            directory, report, code = shrink_scenario(root / "case.json", root / "targets.json", root / "shrinks",
                                                     timeout=2, max_probes=2, **shrink_inputs(root))
            self.assertEqual(code, 2)
            self.assertFalse(report["minimized"])
            self.assertIsNone(report["minimality"])
            self.assertEqual(len(report["probes"]), 2)
            self.assertTrue((directory / "candidate.json").is_file())
            self.assertFalse((directory / "reproducer.json").exists())
            _, replay, code = replay_reproducer(directory, root / "targets.json")
            self.assertEqual(code, 1)
            self.assertTrue(replay["results"][0]["confirmed_mismatch"])

    def test_unsupported_scenario_is_never_labeled_minimized(self):
        with tempfile.TemporaryDirectory() as temporary, fixture_pair("unsupported") as (_, targets):
            root = Path(temporary)
            atomic_json(root / "case.json", fixture_scenario())
            atomic_json(root / "targets.json", targets)
            directory, report, code = shrink_scenario(root / "case.json", root / "targets.json", root / "shrinks", timeout=2, **shrink_inputs(root))
            self.assertEqual(code, 2)
            self.assertFalse(report["minimized"])
            self.assertFalse((directory / "reproducer.json").exists())
            self.assertIn("stable supported", report["error"]["reason"])

    def test_sigterm_finalizes_partial_run(self):
        with tempfile.TemporaryDirectory() as temporary, fixture_pair("hang") as (servers, targets):
            root = Path(temporary)
            cases = root / "scenarios"
            cases.mkdir()
            atomic_json(cases / "case.json", fixture_scenario())
            atomic_json(root / "targets.json", targets)
            process = subprocess.Popen([sys.executable, "-m", "lab", "run", "--targets", str(root / "targets.json"),
                "--scenarios", str(cases), "--output", str(root / "runs"), "--timeout", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(servers[0].probe_requested.wait(5))
                process.send_signal(signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 2, stderr)
                report = json.loads((Path(stdout.strip()) / "report.json").read_text())
                self.assertEqual(report["state"], "interrupted")
                self.assertFalse(report["complete"])
                self.assertEqual(report["summary"]["error"], 1)
                self.assertGreater(len(report["results"][0]["attempts"][0]["targets"]["vanilla"]["commands"]), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
