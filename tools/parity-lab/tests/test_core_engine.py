import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lab.cli import main
from lab.normalize import command_problem, normalize_response
from lab.rcon import AuthenticationError, RconError
from lab.runner import LockError, atomic_json, process_lock, run
from lab.schema import SchemaError, load_scenarios, load_targets, read_json, validate_scenario, validate_targets
from lab.shrink import ShrinkError, ddmin


def scenario():
    return {"schema_version": 1, "id": "stone-placement", "title": "Stone placement", "category": "blocks",
            "description": "Positive block probe", "tags": ["command", "deterministic"],
            "setup": ["fill 0 60 0 8 70 8 minecraft:air"],
            "steps": [{"command": "setblock 2 64 2 minecraft:stone"},
                      {"command": "execute if block 2 64 2 minecraft:stone run say PARITY:stone-present",
                       "observe": True, "expect_contains": "PARITY:stone-present"}],
            "cleanup": ["fill 0 60 0 8 70 8 minecraft:air"], "notes": "Command coverage only."}


def targets():
    return {"schema_version": 1, "minecraft_version": "26.3", "targets": {
        "vanilla": {"host": "127.0.0.1", "port": 25585, "password": "DO-NOT-LOG-THIS"},
        "pumpkin": {"host": "127.0.0.1", "port": 25586, "password": "DO-NOT-LOG-THIS"}}}


class Fixtures:
    """Transport fixtures; actual framing is separately exercised with fake sockets."""
    def __init__(self, responses=None, errors=None):
        self.responses = responses or {}
        self.errors = errors or {}
        self.calls = []
        self.connections = {"vanilla": 0, "pumpkin": 0}

    def factory(self, host, port, password, timeout):
        owner = self
        name = "vanilla" if port == 25585 else "pumpkin"
        number = self.connections[name]
        self.connections[name] += 1

        class Client:
            def connect(self):
                error = owner.errors.get((name, "connect"))
                if error:
                    raise error

            def command(self, command):
                owner.calls.append((name, command))
                value = owner.responses.get((name, command))
                if value is None and "run say" in command:
                    value = f"[{'Rcon' if name == 'vanilla' else 'Server'}] PARITY:stone-present"
                elif value is None:
                    value = "OK"
                if isinstance(value, list):
                    value = value[min(number, len(value) - 1)]
                if isinstance(value, BaseException):
                    raise value
                return value

            def close(self):
                pass
        return Client()


class SchemaTests(unittest.TestCase):
    def test_valid_schema(self):
        self.assertEqual(validate_scenario(scenario())["id"], "stone-placement")
        self.assertEqual(validate_targets(targets())["minecraft_version"], "26.3")

    def test_reject_unsafe_or_ambiguous_scenarios(self):
        changes = [{"schema_version": True}, {"schema_version": 2}, {"id": "Bad_ID"}, {"steps": []},
                   {"steps": [{"command": "say ok", "observe": True}]},
                   {"steps": [{"command": "say ok", "observe": True, "expect_contains": ""}]},
                   {"steps": [{"command": "say ok", "expect_contains": "ok"}]},
                   {"steps": [{"command": "say ok", "observe": True, "expect_contains": "ok", "wait_ticks": True}]},
                   {"steps": [{"command": "say ok", "observe": True, "expect_contains": "ok", "wait_ticks": -1}]},
                   {"setup": ["say first\nsay second"]}, {"unknown": "typo"}, {"tags": ["a", "a"]},
                   {"steps": [{"command": "say ok", "observe": "true", "expect_contains": "ok"}]},
                   {"steps": [{"command": "say ok", "observe": True, "expect_contains": ["ok"]}]}]
        for change in changes:
            with self.subTest(change=change):
                value = scenario()
                value.update(change)
                with self.assertRaises(SchemaError):
                    validate_scenario(value)

    def test_reject_public_targets_and_same_endpoint(self):
        for host in ("0.0.0.0", "example.com", "192.168.1.10"):
            value = targets()
            value["targets"]["vanilla"]["host"] = host
            with self.assertRaises(SchemaError):
                validate_targets(value)
        value = targets()
        value["targets"]["pumpkin"] = value["targets"]["vanilla"].copy()
        with self.assertRaises(SchemaError):
            validate_targets(value)

    def test_malformed_json_never_echoes_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "targets.json"
            for content in ('{"password":"DO-NOT-LOG-THIS",', '{"a":1,"a":2}', '{"value":NaN}'):
                path.write_text(content)
                with self.assertRaises(SchemaError) as caught:
                    read_json(path)
                self.assertNotIn("DO-NOT-LOG-THIS", str(caught.exception))

    def test_directory_selection_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            atomic_json(path / "one.json", scenario())
            self.assertEqual(len(load_scenarios(path)), 1)
            with self.assertRaises(SchemaError):
                load_scenarios(path, "missing")
            atomic_json(path / "two.json", scenario())
            with self.assertRaises(SchemaError):
                load_scenarios(path)


class NormalizationTests(unittest.TestCase):
    def test_known_sender_prefixes_for_chat_and_command_feedback(self):
        for prefix in ("[Rcon] ", "[Server] ", "[RCON] ", "[Not Secure] [Server] "):
            self.assertEqual(normalize_response(prefix + "PARITY:yes", "execute if entity @e run say PARITY:yes"), "PARITY:yes")
            self.assertEqual(normalize_response(prefix + "PARITY:yes", "/say PARITY:yes"), "PARITY:yes")
            self.assertEqual(normalize_response(prefix + "Test passed", "execute if block 0 64 0 stone"), "Test passed")

    def test_output_values_and_whitespace_remain_significant(self):
        for raw in ("[other] message", "UUID:123 count:2", "a\n\n b ", "§aGreen", "{x:1,z:2}"):
            self.assertEqual(normalize_response(raw, "data get entity @e"), raw)
        self.assertNotEqual(normalize_response("[Rcon]  PARITY:x ", "say PARITY:x"), "PARITY:x")
        self.assertNotEqual(normalize_response("{x:1,z:2}", "data get entity @e"), "{z:2,x:1}")
        self.assertEqual(normalize_response("[Server] UUID:123 count:2"), "UUID:123 count:2")

    def test_prefix_does_not_hide_failed_or_unknown_command(self):
        self.assertEqual(command_problem("[Server] Unknown or incomplete command, see below for error"), "unsupported")
        self.assertEqual(command_problem("[Rcon] Test failed"), "command_failed")
        self.assertIsNone(command_problem("[Server] PARITY:stone-present"))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "runs"
        self.lock = Path(self.temp.name) / "lock"
        self.case = scenario()
        self.observe = self.case["steps"][1]["command"]

    def execute(self, fixture=None, repeat=1, cases=None):
        self.fixture = fixture or Fixtures()
        return run(cases or [self.case], targets(), self.output, repeat=repeat,
                   client_factory=self.fixture.factory, lock_path=self.lock)

    def test_semantic_prefix_parity_preserves_evidence(self):
        directory, report, code = self.execute(repeat=2)
        self.assertEqual(code, 0)
        self.assertEqual(report["summary"], {"passed": 1, "different": 0, "error": 0, "total": 1})
        result = report["results"][0]
        self.assertFalse(result["flaky"])
        self.assertIn("[Rcon]", result["observations"]["vanilla"][0])
        self.assertIn("[Server]", result["observations"]["pumpkin"][0])
        self.assertTrue(report["complete"])
        self.assertEqual(read_json(directory / "report.json"), report)
        self.assertEqual(read_json(directory / "scenarios" / "stone-placement.json"), self.case)
        self.assertIn("RCON command", report["command_coverage"]["scope"])
        for path in directory.rglob("*"):
            if path.is_file():
                self.assertNotIn("DO-NOT-LOG-THIS", path.read_text())
        events = [json.loads(line) for line in (directory / "transcripts" / "vanilla.jsonl").read_text().splitlines()]
        self.assertTrue(any(e.get("raw", "").startswith("[Rcon]") for e in events))
        # Each target runs its whole attempt serially, then the other target.
        self.assertEqual([n for n, _ in self.fixture.calls], ["vanilla"] * 4 + ["pumpkin"] * 4 + ["vanilla"] * 4 + ["pumpkin"] * 4)

    def test_two_equal_empty_or_failed_probes_never_pass(self):
        for raw in ("", "Test failed", "[Server] Unknown or incomplete command"):
            with self.subTest(raw=raw):
                fixtures = Fixtures({(name, self.observe): raw for name in ("vanilla", "pumpkin")})
                _, report, code = self.execute(fixtures)
                self.assertEqual(code, 1)
                self.assertEqual(report["results"][0]["status"], "different")
                self.assertIn("expectation_failed", report["results"][0]["reason"])
                self.assertFalse(report["results"][0]["confirmed_mismatch"])

    def test_expectation_checked_on_both_targets(self):
        fixture = Fixtures({("pumpkin", self.observe): "[Server] PARITY:wrong"})
        _, report, code = self.execute(fixture, repeat=2)
        self.assertEqual(code, 1)
        self.assertTrue(report["results"][0]["confirmed_mismatch"])
        failures = report["results"][0]["attempts"][0]["failures"]
        self.assertTrue(any(f["kind"] == "expectation_failed" and f["target"] == "pumpkin" for f in failures))

    def test_narrow_normalization_detects_real_payload_difference(self):
        fixtures = Fixtures({("pumpkin", self.observe): "[Server] PARITY:stone-present extra"})
        _, report, code = self.execute(fixtures)
        self.assertEqual(code, 1)
        self.assertIn("observation_mismatch", report["results"][0]["reason"])
        self.assertFalse(report["results"][0]["confirmed_mismatch"], "one repeat is only a candidate")

    def test_flaky_repeats_excluded_from_confirmed_mismatch(self):
        fixtures = Fixtures({("pumpkin", self.observe): ["[Server] PARITY:stone-present extra", "[Server] PARITY:stone-present"]})
        _, report, code = self.execute(fixtures, repeat=2)
        self.assertEqual(code, 1)
        self.assertTrue(report["results"][0]["flaky"])
        self.assertEqual(report["confirmed_mismatch_count"], 0)

    def test_equal_between_targets_but_changing_across_repeats_is_flaky(self):
        fixtures = Fixtures({(name, self.observe): ["[Server] PARITY:stone-present A", "[Server] PARITY:stone-present B"] for name in ("vanilla", "pumpkin")})
        _, report, code = self.execute(fixtures, repeat=2)
        self.assertEqual(code, 1)
        self.assertTrue(report["results"][0]["flaky"])

    def test_auth_or_disconnect_is_infra_and_other_target_runs(self):
        for error in (AuthenticationError("auth rejected"), RconError("disconnected")):
            fixtures = Fixtures(errors={("vanilla", "connect"): error})
            _, report, code = self.execute(fixtures)
            self.assertEqual(code, 2)
            self.assertEqual(report["results"][0]["status"], "error")
            self.assertTrue(any(name == "pumpkin" for name, _ in fixtures.calls))

    def test_cleanup_runs_after_expectation_and_transport_failure(self):
        fixtures = Fixtures({("vanilla", self.observe): RconError("connection reset")})
        _, report, code = self.execute(fixtures)
        self.assertEqual(code, 2)
        self.assertIn(("vanilla", self.case["cleanup"][0]), fixtures.calls)

    def test_unknown_unobserved_command_is_visible(self):
        command = self.case["steps"][0]["command"]
        fixtures = Fixtures({(name, command): "Unknown or incomplete command, see below for error" for name in ("vanilla", "pumpkin")})
        _, report, code = self.execute(fixtures, repeat=2)
        self.assertEqual(code, 1)
        self.assertIn("unsupported", report["results"][0]["reason"])
        self.assertFalse(report["results"][0]["confirmed_mismatch"])
        self.assertEqual(report["command_coverage"]["targets"]["vanilla"]["setblock"]["unsupported"], 2)

    def test_interruption_preserves_atomic_report_and_pending_transcript(self):
        fixtures = Fixtures({("vanilla", self.observe): KeyboardInterrupt()})
        second = scenario()
        second["id"] = "zzz-next"
        directory, report, code = self.execute(fixtures, cases=[self.case, second])
        self.assertEqual(code, 2)
        self.assertEqual(report["state"], "interrupted")
        self.assertFalse(report["complete"])
        self.assertEqual(report["summary"]["error"], 2)
        self.assertEqual(report["results"][1]["reason"], "Not run")
        self.assertEqual(read_json(directory / "report.json"), report)
        self.assertIn(self.observe, (directory / "transcripts" / "vanilla.jsonl").read_text())

    def test_tick_capability_gap_cannot_pass(self):
        self.case["steps"][0]["wait_ticks"] = 2
        fixtures = Fixtures({(name, "tick query"): "Unknown command" for name in ("vanilla", "pumpkin")})
        _, report, code = self.execute(fixtures)
        self.assertEqual(code, 1)
        self.assertIn("unsupported", report["results"][0]["reason"])

    def test_tick_steps_verified_with_game_time_and_restored(self):
        self.case["steps"][0]["wait_ticks"] = 2
        fixture = Fixtures()
        original_factory = fixture.factory
        def factory(*args, **kwargs):
            client = original_factory(*args, **kwargs)
            original_command = client.command
            state = {"time": 10}
            def command(text):
                if text == "tick query":
                    return "The game is running normally at 20 ticks per second"
                if text == "tick freeze":
                    return "The game is now frozen"
                if text == "tick unfreeze":
                    return "The game is now running normally"
                if text == "time query gametime":
                    return f"The time is {state['time']}"
                if text == "tick step 2":
                    state["time"] += 2
                    return "Stepping 2 ticks"
                return original_command(text)
            client.command = command
            return client
        fixture.factory = factory
        _, report, code = self.execute(fixture)
        self.assertEqual(code, 0)
        for target in report["results"][0]["attempts"][0]["targets"].values():
            self.assertTrue(any(c["command"] == "tick unfreeze" for c in target["commands"]))

    def test_global_lock_blocks_another_process(self):
        script = "from lab.runner import process_lock,LockError\nimport sys\ntry:\n with process_lock(sys.argv[1],0.05): pass\nexcept LockError: sys.exit(7)\n"
        with process_lock(self.lock):
            child = subprocess.run([sys.executable, "-c", script, str(self.lock)], capture_output=True, text=True)
        self.assertEqual(child.returncode, 7, child.stderr)


class ShrinkTests(unittest.TestCase):
    def test_real_delta_debugging_preserves_order_and_removes_noise(self):
        calls = []
        def fails(sequence):
            calls.append(list(sequence))
            return "create" in sequence and "probe" in sequence and sequence.index("create") < sequence.index("probe")
        result = ddmin(["noise-a", "create", "noise-b", "probe", "noise-c"], fails)
        self.assertEqual(result, ["create", "probe"])
        self.assertEqual(calls[-1], result, "final result must be rerun")
        self.assertTrue(all(not fails(result[:i] + result[i + 1:]) for i in range(len(result))))

    def test_nonmonotonic_predicate_and_single_element(self):
        result = ddmin([1, 2, 3, 4], lambda seq: len(seq) in (1, 4))
        self.assertEqual(len(result), 1)
        self.assertEqual(ddmin([1], lambda seq: 1 in seq), [1])
        self.assertEqual(ddmin([1, 2], lambda seq: True), [])

    def test_non_failure_and_unstable_final_rerun_rejected(self):
        with self.assertRaises(ShrinkError):
            ddmin([1, 2], lambda seq: False)
        seen = 0
        def unstable(seq):
            nonlocal seen
            if seq == [1]:
                seen += 1
                return seen == 1
            return False
        with self.assertRaises(ShrinkError):
            ddmin([1], unstable)


class CliTests(unittest.TestCase):
    def test_list_json_and_malformed_targets_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "scenarios"
            cases.mkdir()
            atomic_json(cases / "stone.json", scenario())
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(main(["list", "--scenarios", str(cases)]), 0)
            self.assertEqual(json.loads(output.getvalue())["scenarios"][0]["id"], "stone-placement")
            config = root / "targets.json"
            config.write_text('{"password":"DO-NOT-LOG-THIS",')
            with redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(main(["run", "--targets", str(config), "--scenarios", str(cases), "--output", str(root / "runs")]), 2)
            self.assertNotIn("DO-NOT-LOG-THIS", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
