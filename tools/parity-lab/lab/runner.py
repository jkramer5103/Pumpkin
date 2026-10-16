"""Serial, locked execution with durable evidence and conservative verdicts."""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import fcntl
import json
import os
import random
import re
import signal
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from .normalize import command_problem, normalize_response, strip_sender
from .rcon import RconClient, RconError
from .schema import validate_scenario, validate_targets
from .provenance import binary_identity, check_transports, verify_versions, world_identity
from . import __version__

TARGET_NAMES = ("vanilla", "pumpkin")
NORMALIZATION = "v1: strip [Rcon], [RCON], [Server] and optional [Not Secure] wrappers at line starts only; preserve all other text"


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, value):
    """Replace a complete JSON document and fsync both file and directory."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class LockError(RconError):
    pass


@contextlib.contextmanager
def interruption_signals():
    """Give SIGTERM the same durable cleanup/report path as Ctrl-C."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(signum, frame):
        raise KeyboardInterrupt("Received SIGTERM")

    signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@contextlib.contextmanager
def process_lock(path=None, timeout=30.0):
    # The lock does not depend on the output directory: concurrent invocations
    # writing different artifacts must still serialize access to the same worlds.
    path = Path(path or Path(tempfile.gettempdir()) / f"pumpkin-parity-lab-{os.getuid()}.lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockError("Timed out waiting for the lab process lock")
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        yield
    finally:
        # Closing releases the lock; never unlink a lock another process may hold.
        os.close(fd)


class Transcript:
    def __init__(self, path):
        self.handle = Path(path).open("x", encoding="utf-8")

    def write(self, event):
        self.handle.write(json.dumps({"at": utc_now(), **event}, ensure_ascii=False) + "\n")
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def close(self):
        self.handle.close()


class UnsupportedTicks(Exception):
    pass


class TickController:
    """Freeze, step, and verify game-time advancement rather than wall-clock sleep.

    wait_ticks advances simulation AFTER its step command. All commands in a
    scenario with waits run frozen. A game-time barrier confirms every requested
    tick actually ran. Unknown tick/query formats are visible capability gaps.
    """

    def __init__(self, execute, timeout):
        self.execute, self.timeout = execute, timeout
        self.restore = False

    def _call(self, command):
        raw = self.execute(command, "timing")
        if command_problem(raw):
            raise UnsupportedTicks(f"Deterministic timing unavailable: {command}")
        return raw

    def freeze(self):
        response = self._call("tick query").lower()
        if "game is frozen" in response:
            return
        if "game is running" not in response:
            raise UnsupportedTicks("Cannot determine existing tick freeze state")
        # Restore even if the freeze request applies but its reply is lost.
        self.restore = True
        response = self._call("tick freeze").lower()
        if "frozen" not in response:
            raise UnsupportedTicks("Cannot verify tick freeze")

    def game_time(self):
        raw = self._call("time query gametime")
        # These are explicit game-time response grammars, not output
        # normalization. The 26.3 vanilla and Pumpkin phrasings differ.
        value = re.fullmatch(r"(?:(?:The )?[Tt]ime is |The game time is |Gametime is )(\d+)(?: tick\(s\))?\s*", strip_sender(raw))
        if not value:
            raise UnsupportedTicks("Cannot parse time query gametime for deterministic timing")
        return int(value[1])

    def advance(self, ticks):
        before = self.game_time()
        self._call(f"tick step {ticks}")
        deadline = time.monotonic() + max(self.timeout, ticks / 20 + 5)
        while True:
            after = self.game_time()
            elapsed = (after - before) % 2147483647
            if elapsed == ticks:
                return
            if elapsed > ticks:
                raise UnsupportedTicks("Simulation advanced beyond requested ticks")
            if time.monotonic() >= deadline:
                raise RconError("Timed out verifying deterministic tick advancement")
            time.sleep(0.01)

    def close(self):
        if self.restore:
            raw = self.execute("tick unfreeze", "timing_cleanup")
            if command_problem(raw) or "running" not in raw.lower():
                raise RconError("Could not verify restoration of tick state")


def _target_record():
    return {"observations": [], "commands": [], "problems": [], "errors": [], "completed": False,
            "timing": {"status": "untested", "verified_ticks": 0}}


def _attempt_target(scenario, target, target_name, repeat, transcript, factory, timeout, record,
                    reset_commands=(), checkpoint=lambda: None):
    client = None
    ticks = None
    connected_once = False
    transport_broken = False

    def execute(command, phase, index=None):
        event = {"scenario_id": scenario["id"], "repeat": repeat, "target": target_name,
                 "phase": phase, "index": index, "command": command}
        # Persist the request first, so an interruption leaves a visible pending command.
        transcript.write({**event, "event": "request"})
        record["pending_command"] = event
        checkpoint()
        try:
            raw = client.command(command)
        except BaseException as exc:
            transcript.write({**event, "event": "error", "error": str(exc), "error_type": type(exc).__name__,
                              "received_wire_hex": bytes(getattr(client, "last_wire_bytes", b"")).hex(),
                              "response_packets_hex": [p.hex() for p in getattr(client, "last_response_packets", [])]})
            record.setdefault("uncertain_commands", []).append({**event, "error_type": type(exc).__name__})
            record.pop("pending_command", None)
            checkpoint()
            raise
        problem = command_problem(raw)
        packets = [p.hex() for p in getattr(client, "last_response_packets", [])]
        record["commands"].append({**event, "raw": raw, "problem": problem, "response_packets_hex": packets})
        record.pop("pending_command", None)
        transcript.write({**event, "event": "response", "raw": raw, "problem": problem, "response_packets_hex": packets})
        if problem == "environment_error":
            record["errors"].append({"kind": "EnvironmentError", "phase": phase, "command": command, "reason": raw})
        # kill of an already-empty arena is an expected idempotent setup/cleanup.
        benign_empty_kill = (phase in ("reset", "setup", "cleanup") and command.lstrip("/").startswith("kill ")
                             and re.match(r"No (?:entity|entities) (?:was |were )?found", strip_sender(raw)))
        if problem in ("unsupported", "command_failed") and not benign_empty_kill:
            record["problems"].append({"phase": phase, "index": index, "command": command, "kind": problem})
        checkpoint()
        return raw

    try:
        client = factory(target["host"], target["port"], target["password"], timeout=timeout)
        transcript.write({"scenario_id": scenario["id"], "repeat": repeat, "target": target_name,
                          "event": "connecting", "host": target["host"], "port": target["port"]})
        client.connect()
        connected_once = True
        if hasattr(client, "directory"):
            world = Path(client.directory) / "world"
            record["world_identity"] = (world_identity(world) if world.is_dir() else
                                         {"status": "unknown", "scratch_directory": str(client.directory)})
        transcript.write({"scenario_id": scenario["id"], "repeat": repeat, "target": target_name, "event": "connected"})
        checkpoint()
        if any(step.get("wait_ticks", 0) for step in scenario["steps"]):
            record["timing"]["status"] = "testing"
            ticks = TickController(execute, timeout)
            ticks.freeze()
        for index, command in enumerate(reset_commands):
            raw = execute(command, "reset", index)
            # A failed reset leaves unknown state; never execute the candidate.
            if command_problem(raw) and record["problems"] + record["errors"]:
                raise RconError("Arena reset failed; candidate was not executed")
        for index, command in enumerate(scenario["setup"]):
            execute(command, "setup", index)
        for index, step in enumerate(scenario["steps"]):
            raw = execute(step["command"], "steps", index)
            if step.get("observe", False):
                normalized = normalize_response(raw, step["command"])
                expected = step.get("expect_contains")
                record["observations"].append({"index": index, "command": step["command"],
                    "raw": raw, "normalized": normalized, "expect_contains": expected,
                    "expectation_met": expected in normalized if expected is not None else None})
                checkpoint()
            if step.get("wait_ticks", 0):
                ticks.advance(step["wait_ticks"])
                record["timing"]["verified_ticks"] += step["wait_ticks"]
                record["timing"]["status"] = "supported"
                checkpoint()
        record["completed"] = True
    except UnsupportedTicks as exc:
        record["timing"].update(status="unsupported", reason=str(exc))
        record["problems"].append({"phase": "timing", "kind": "unsupported", "reason": str(exc)})
    except RconError as exc:
        transport_broken = True
        record["errors"].append({"kind": type(exc).__name__, "reason": str(exc)})
        transcript.write({"scenario_id": scenario["id"], "repeat": repeat, "target": target_name,
                          "event": "target_error", "error_type": type(exc).__name__, "error": str(exc)})
    except BaseException as exc:
        transport_broken = True
        record["errors"].append({"kind": type(exc).__name__, "reason": "Interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)})
        raise
    finally:
        # Continue cleanup after a failed command, reconnecting before the next
        # one. In particular, a final explicit tick unfreeze must not be skipped
        # just because an earlier cleanup command lost its connection.
        # Commands with lost responses are never replayed automatically.
        if client is not None:
            def reconnect_if_broken():
                nonlocal client, transport_broken
                if transport_broken:
                    client.close()
                    if not getattr(client, "reconnectable", True):
                        raise RconError("Scratch console disconnected; automatic reconnect cannot preserve the world session")
                    client = factory(target["host"], target["port"], target["password"], timeout=timeout)
                    client.connect()
                    transport_broken = False

            try:
                # Failed authentication/connection cannot have mutated the world.
                # Do not return from finally: that would suppress an interrupt.
                for index, command in enumerate(scenario["cleanup"] if connected_once else []):
                    try:
                        reconnect_if_broken()
                    except RconError as exc:
                        record["errors"].append({"kind": type(exc).__name__, "reason": "Cleanup connection: " + str(exc)})
                        break
                    try:
                        execute(command, "cleanup", index)
                    except RconError as exc:
                        transport_broken = True
                        record["errors"].append({"kind": type(exc).__name__, "reason": "Cleanup: " + str(exc)})
                try:
                    if ticks and ticks.restore:
                        reconnect_if_broken()
                        ticks.close()
                except RconError as exc:
                    record["errors"].append({"kind": type(exc).__name__, "reason": "Tick restoration: " + str(exc)})
            finally:
                client.close()
        if record["timing"]["status"] != "untested" and record["errors"]:
            record["timing"]["status"] = "error"
    return record


def compare_attempt(targets):
    failures = []
    for name, record in targets.items():
        failures.extend({"kind": "infrastructure_error", "target": name, "error": error}
                        for error in record["errors"])
        failures.extend({"target": name, **problem} for problem in record["problems"])
        for observation in record["observations"]:
            if not observation["normalized"].strip():
                failures.append({"kind": "empty_observation", "target": name,
                                 "index": observation["index"], "command": observation["command"]})
            if observation["expectation_met"] is False:
                failures.append({"kind": "expectation_failed", "target": name,
                                 "index": observation["index"], "command": observation["command"],
                                 "expected": observation["expect_contains"]})
        if not record["completed"] and not record["problems"] and not record["errors"]:
            failures.append({"kind": "infrastructure_error", "target": name,
                             "error": {"kind": "IncompleteTarget", "reason": "Target did not complete"}})
    vanilla, pumpkin = (targets[name]["observations"] for name in TARGET_NAMES)
    left = [(o["index"], o["normalized"]) for o in vanilla]
    right = [(o["index"], o["normalized"]) for o in pumpkin]
    if left != right:
        failures.append({"kind": "observation_mismatch"})
    if not vanilla or not pumpkin:
        failures.append({"kind": "missing_observations"})
    if failures:
        kinds = sorted({failure["kind"] for failure in failures})
        status = "error" if "infrastructure_error" in kinds else "different"
        return {"status": status, "reason": ", ".join(kinds), "failures": failures}
    return {"status": "pass", "reason": "Observations agree and positive expectations passed on both targets", "failures": []}


def _fingerprint(attempt):
    return json.dumps({"status": attempt["status"], "failures": attempt["failures"],
        "targets": {name: {"observations": [(o["index"], o["normalized"], o["expectation_met"])
                                           for o in record["observations"]],
                           "problems": record["problems"], "errors": record["errors"]}
                    for name, record in attempt["targets"].items()}}, sort_keys=True)


def summarize_result(result):
    attempts = result["attempts"]
    # Only complete, compared attempts can establish repeat stability.
    if not attempts or any("status" not in a for a in attempts):
        return
    result["flaky"] = len({_fingerprint(a) for a in attempts}) > 1
    if any(a["status"] == "error" for a in attempts):
        result["status"] = "error"
        result["reason"] = "Infrastructure failure in one or more repeats"
    elif result["flaky"]:
        result["status"] = "different"
        result["reason"] = "Flaky: repeat outcomes/observations changed; excluded from confirmed mismatches"
    else:
        result["status"] = attempts[0]["status"]
        result["reason"] = attempts[0]["reason"]
    result["observations"] = {name: [o["raw"] for o in attempts[0]["targets"][name]["observations"]]
                              for name in TARGET_NAMES}
    unsupported = any(f["kind"] == "unsupported" for a in attempts for f in a["failures"])
    # A failed reference command in any phase invalidates the comparison's
    # preconditions even when a later positive assertion happens to pass.
    vanilla_failed = any(f["kind"] in ("expectation_failed", "command_failed")
                         and f.get("target") == "vanilla"
                         for a in attempts for f in a["failures"])
    result["confirmed_mismatch"] = (len(attempts) >= 2 and not result["flaky"] and not unsupported
        and not vanilla_failed
        and result["status"] == "different"
        and any(f["kind"] == "observation_mismatch" for f in attempts[0]["failures"]))
    result["repeat_count"] = len(attempts)
    result["trial_details"] = {
        "series_complete": len(attempts) == result.get("requested_repeat_count", len(attempts)),
        "outcome_counts": {status: sum(a["status"] == status for a in attempts)
                           for status in ("pass", "different", "error")},
        "distinct_outcomes": len({_fingerprint(a) for a in attempts}),
        "target_variability": {name: len({json.dumps({
            "observations": [(o["index"], o["normalized"], o["expectation_met"])
                             for o in a["targets"][name]["observations"]],
            "problems": a["targets"][name]["problems"],
            "errors": a["targets"][name]["errors"]}, sort_keys=True) for a in attempts}) > 1
            for name in TARGET_NAMES},
        "classification": ("infrastructure_error" if result["status"] == "error" else
                           "non_deterministic" if result["flaky"] else
                           "single_trial" if len(attempts) < 2 else
                           "confirmed_mismatch" if result["confirmed_mismatch"] else
                           "stable_unsupported" if unsupported else
                           "stable_pass" if result["status"] == "pass" else "stable_failure"),
    }
    if not result["trial_details"]["series_complete"]:
        result["status"] = "error"
        result["confirmed_mismatch"] = False
        result["reason"] = "Awaiting remaining trials"
        result["trial_details"]["classification"] = "incomplete"


def _update_summary(report):
    summary = {"passed": 0, "different": 0, "error": 0, "total": len(report["results"])}
    for result in report["results"]:
        summary[{"pass": "passed", "different": "different", "error": "error"}[result["status"]]] += 1
    report["summary"] = summary
    report["flaky_count"] = sum(r.get("flaky", False) for r in report["results"])
    report["confirmed_mismatch_count"] = sum(r.get("confirmed_mismatch", False) for r in report["results"])
    coverage = {name: {} for name in TARGET_NAMES}
    for result in report["results"]:
        for attempt in result["attempts"]:
            for name, target in attempt["targets"].items():
                for event in target["commands"]:
                    command = event["command"].lstrip("/").split()[0]
                    entry = coverage[name].setdefault(command, {"responses": 0, "unsupported": 0, "failed": 0})
                    entry["responses"] += 1
                    entry["unsupported"] += event["problem"] == "unsupported"
                    entry["failed"] += event["problem"] == "command_failed"
    scope = ("RCON and scratch-console command observations only; no client gameplay coverage"
             if report.get("transports", {}).get("pumpkin") == "scratch-console"
             else "RCON command observations only; no client gameplay coverage")
    report["command_coverage"] = {"scope": scope, "targets": coverage}
    report["unsupported_commands"] = {name: sorted({event["command"] for result in report["results"]
        for attempt in result["attempts"] for event in attempt["targets"].get(name, {}).get("commands", [])
        if event["problem"] == "unsupported"}) for name in TARGET_NAMES}


def run(scenarios, targets, output, *, repeat=1, timeout=10.0, lock_timeout=30.0,
        client_factory=RconClient, lock_path=None, reset_commands=(), pumpkin_console=None,
        order="alternating", order_seed=0, probe_ticks=False, console_arena=False,
        target_versions=None):
    """Return (run_directory, report, exit_code). No connection before validation/lock."""
    validate_targets(targets)
    if type(repeat) is not int or repeat < 1:
        raise ValueError("repeat must be a positive integer")
    if order not in ("sorted", "alternating", "shuffle") or type(order_seed) is not int:
        raise ValueError("order must be sorted, alternating or shuffle; order_seed must be an integer")
    if type(probe_ticks) is not bool:
        raise ValueError("probe_ticks must be a boolean")
    if not 0 < timeout <= 300 or not 0 <= lock_timeout <= 300:
        raise ValueError("timeout must be > 0 and <= 300; lock_timeout must be >= 0 and <= 300")
    if not scenarios:
        raise ValueError("at least one scenario is required")
    for scenario in scenarios:
        validate_scenario(scenario)
    if len({s["id"] for s in scenarios}) != len(scenarios):
        raise ValueError("duplicate scenario ids")
    if reset_commands:
        validate_scenario({**scenarios[0], "setup": list(reset_commands)})
    if pumpkin_console is not None:
        pumpkin_console = Path(pumpkin_console).resolve()
        if not pumpkin_console.is_file() or not os.access(pumpkin_console, os.X_OK):
            raise ValueError("pumpkin_console must name an executable binary")
    versions = verify_versions(target_versions) if target_versions is not None else None
    if versions is not None:
        check_transports(versions, pumpkin_console)
    console_identity = binary_identity(pumpkin_console) if pumpkin_console else None
    targets = copy.deepcopy(targets)
    scenarios = copy.deepcopy(sorted(scenarios, key=lambda s: s["id"]))
    generator = random.Random(order_seed)
    schedule = []
    for number in range(1, repeat + 1):
        trial = list(range(len(scenarios)))
        if order == "alternating" and number % 2 == 0:
            trial.reverse()
        elif order == "shuffle":
            generator.shuffle(trial)
        schedule.extend((number, index, position) for position, index in enumerate(trial))
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:8]
    directory = Path(output).resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "scenarios").mkdir()
    (directory / "transcripts").mkdir()
    report = {"schema_version": 1, "run_id": run_id, "started_at": utc_now(), "finished_at": None,
              "engine_version": __version__, "python_version": sys.version.split()[0],
              "minecraft_version": targets["minecraft_version"], "state": "running", "complete": False,
              "repeat": repeat, "normalization": NORMALIZATION, "console_arena": console_arena,
              "reset_commands": list(reset_commands),
              "isolation": {"policy": "declared_reset" if reset_commands else "scenario_setup_cleanup",
                            "world_snapshot": False, "order": order, "order_seed": order_seed,
                            "scope": "Setup/cleanup and optional reset run per target/trial; arbitrary state restoration is not proven"},
              "trial_schedule": [{"repeat": number, "id": scenarios[index]["id"], "position": position}
                                 for number, index, position in schedule],
              "timing_capabilities": {name: {"status": "untested"} for name in TARGET_NAMES},
              "transports": {"vanilla": "rcon", "pumpkin": "scratch-console" if pumpkin_console else "rcon"},
              "targets": {name: {"host": t["host"], "port": t["port"]} for name, t in targets["targets"].items()},
              "target_versions": versions,
              "provenance_limitations": "Versions and RCON world paths are declarations, not service attestation. Local binary hashes and optional directory identities are checked; world contents, seeds and snapshots are not verified.",
              "results": [{"id": s["id"], "title": s["title"], "category": s["category"],
                           "status": "error", "observations": {name: [] for name in TARGET_NAMES},
                           "reason": "Not run", "duration_seconds": 0.0, "attempts": [],
                           "requested_repeat_count": repeat,
                           "flaky": False, "confirmed_mismatch": False} for s in scenarios]}
    from .recovery import process_identity
    report["owner"] = process_identity()

    if pumpkin_console:
        report["targets"]["pumpkin"] = {**console_identity, "transport": "scratch-console"}

    def save():
        _update_summary(report)
        atomic_json(directory / "report.json", report)

    save()
    # Snapshot every input before lock acquisition, including timed-out runs.
    for scenario in scenarios:
        atomic_json(directory / "scenarios" / (scenario["id"] + ".json"), scenario)
    transcripts = {}
    current = None
    start = None
    try:
        with interruption_signals(), process_lock(lock_path, lock_timeout):
            for name in TARGET_NAMES:
                transcripts[name] = Transcript(directory / "transcripts" / (name + ".jsonl"))

            def target_factory(name, scenario_id, number):
                if versions is not None:
                    verify_versions(versions)
                if name == "pumpkin" and pumpkin_console:
                    if binary_identity(pumpkin_console) != console_identity:
                        raise ValueError("Scratch console binary changed during the run")
                    from .console import ConsoleClient
                    console_directory = directory / "console" / (scenario_id + "-" + str(number))
                    return lambda host, port, password, timeout: ConsoleClient(
                        pumpkin_console, console_directory, timeout=timeout, arena=console_arena)
                return client_factory

            if probe_ticks:
                probe = {"id": "timing-capability-probe", "setup": [], "cleanup": [],
                         "steps": [{"command": "time query gametime", "wait_ticks": 1}]}
                for name in TARGET_NAMES:
                    record = _target_record()
                    report["timing_capabilities"][name] = record
                    # Save the mutable record before connecting, including interruptions.
                    record["status"] = "testing"
                    save()
                    _attempt_target(probe, targets["targets"][name], name, 0, transcripts[name],
                        target_factory(name, probe["id"], 0), timeout, record, checkpoint=save)
                    record["status"] = "error" if record["errors"] else record["timing"]["status"]
                    save()

            for number, scenario_index, position in schedule:
                scenario = scenarios[scenario_index]
                current = report["results"][scenario_index]
                start = time.monotonic()
                current["reason"] = "Running; no verdict yet"
                save()
                attempt = {"repeat": number, "position": position, "targets": {}}
                # Append first to preserve partial attempts on interruption.
                current["attempts"].append(attempt)
                for name in TARGET_NAMES:
                    record = _target_record()
                    attempt["targets"][name] = record
                    _attempt_target(scenario, targets["targets"][name], name,
                        number, transcripts[name], target_factory(name, scenario["id"], number),
                        timeout, record, reset_commands, checkpoint=save)
                    save()
                attempt.update(compare_attempt(attempt["targets"]))
                summarize_result(current)
                current["duration_seconds"] = round(current["duration_seconds"] + time.monotonic() - start, 6)
                save()
            report["complete"] = True
            report["state"] = "finished"
    except (Exception, KeyboardInterrupt) as exc:
        # Catch unexpected engine exceptions too: the artifact is explicitly an
        # infrastructure failure with its type, never a fabricated parity pass.
        report["state"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        report["complete"] = False
        report["error"] = {"kind": type(exc).__name__, "reason": str(exc)}
        if current is not None:
            current["status"] = "error"
            current["confirmed_mismatch"] = False
            current["reason"] = "Interrupted" if isinstance(exc, KeyboardInterrupt) else "Engine/infrastructure failure"
            current["duration_seconds"] = round(current["duration_seconds"] + time.monotonic() - start, 6)
            if current["attempts"]:
                current["observations"] = {name: [o["raw"] for o in current["attempts"][0]["targets"].get(name, {}).get("observations", [])]
                                           for name in TARGET_NAMES}
        # Completed attempts survive; partial attempt shape remains documented.
    finally:
        for transcript in transcripts.values():
            transcript.close()
        for capability in report["timing_capabilities"].values():
            if capability["status"] == "testing":
                capability["status"] = "error"
                capability["reason"] = "Timing capability probe did not complete"
        report["finished_at"] = utc_now()
        save()
    capabilities = [c["status"] for c in report["timing_capabilities"].values()]
    code = (2 if not report["complete"] or report["summary"]["error"] or "error" in capabilities
            else 1 if report["summary"]["different"] or "unsupported" in capabilities else 0)
    return directory, report, code
