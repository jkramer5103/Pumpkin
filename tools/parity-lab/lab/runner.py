"""Serial, locked execution with durable evidence and conservative verdicts."""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import fcntl
import json
import os
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
    return {"observations": [], "commands": [], "problems": [], "errors": [], "completed": False}


def _attempt_target(scenario, target, target_name, repeat, transcript, factory, timeout, record):
    client = None
    ticks = None
    connected_once = False
    transport_broken = False

    def execute(command, phase, index=None):
        event = {"scenario_id": scenario["id"], "repeat": repeat, "target": target_name,
                 "phase": phase, "index": index, "command": command}
        # Persist the request first, so an interruption leaves a visible pending command.
        transcript.write({**event, "event": "request"})
        try:
            raw = client.command(command)
        except RconError as exc:
            transcript.write({**event, "event": "error", "error": str(exc), "error_type": type(exc).__name__,
                              "received_wire_hex": bytes(getattr(client, "last_wire_bytes", b"")).hex(),
                              "response_packets_hex": [p.hex() for p in getattr(client, "last_response_packets", [])]})
            raise
        problem = command_problem(raw)
        packets = [p.hex() for p in getattr(client, "last_response_packets", [])]
        record["commands"].append({**event, "raw": raw, "problem": problem, "response_packets_hex": packets})
        transcript.write({**event, "event": "response", "raw": raw, "problem": problem, "response_packets_hex": packets})
        if problem == "environment_error":
            record["errors"].append({"kind": "EnvironmentError", "phase": phase, "command": command, "reason": raw})
        # kill of an already-empty arena is an expected idempotent setup/cleanup.
        benign_empty_kill = (phase in ("setup", "cleanup") and command.lstrip("/").startswith("kill ")
                             and re.match(r"No (?:entity|entities) (?:was |were )?found", strip_sender(raw)))
        if problem in ("unsupported", "command_failed") and not benign_empty_kill:
            record["problems"].append({"phase": phase, "index": index, "command": command, "kind": problem})
        return raw

    try:
        client = factory(target["host"], target["port"], target["password"], timeout=timeout)
        transcript.write({"scenario_id": scenario["id"], "repeat": repeat, "target": target_name,
                          "event": "connecting", "host": target["host"], "port": target["port"]})
        client.connect()
        connected_once = True
        transcript.write({"scenario_id": scenario["id"], "repeat": repeat, "target": target_name, "event": "connected"})
        if any(step.get("wait_ticks", 0) for step in scenario["steps"]):
            ticks = TickController(execute, timeout)
            ticks.freeze()
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
            if step.get("wait_ticks", 0):
                ticks.advance(step["wait_ticks"])
        record["completed"] = True
    except UnsupportedTicks as exc:
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
    # A broken vanilla oracle cannot establish the intended behavior. Keep the
    # difference visible, but require its positive assertions before confirmation.
    vanilla_failed = any(f["kind"] == "expectation_failed" and f.get("target") == "vanilla"
                         for a in attempts for f in a["failures"])
    result["confirmed_mismatch"] = (len(attempts) >= 2 and not result["flaky"] and not unsupported
        and not vanilla_failed
        and result["status"] == "different"
        and any(f["kind"] == "observation_mismatch" for f in attempts[0]["failures"]))
    result["repeat_count"] = len(attempts)


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
    report["command_coverage"] = {"scope": "RCON command observations only; no client gameplay coverage", "targets": coverage}
    report["unsupported_commands"] = {name: sorted({event["command"] for result in report["results"]
        for attempt in result["attempts"] for event in attempt["targets"].get(name, {}).get("commands", [])
        if event["problem"] == "unsupported"}) for name in TARGET_NAMES}


def run(scenarios, targets, output, *, repeat=1, timeout=10.0, lock_timeout=30.0,
        client_factory=RconClient, lock_path=None):
    """Return (run_directory, report, exit_code). No connection before validation/lock."""
    validate_targets(targets)
    if type(repeat) is not int or repeat < 1:
        raise ValueError("repeat must be a positive integer")
    if not 0 < timeout <= 300 or not 0 <= lock_timeout <= 300:
        raise ValueError("timeout must be > 0 and <= 300; lock_timeout must be >= 0 and <= 300")
    if not scenarios:
        raise ValueError("at least one scenario is required")
    for scenario in scenarios:
        validate_scenario(scenario)
    if len({s["id"] for s in scenarios}) != len(scenarios):
        raise ValueError("duplicate scenario ids")
    scenarios = copy.deepcopy(sorted(scenarios, key=lambda s: s["id"]))
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:8]
    directory = Path(output).resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "scenarios").mkdir()
    (directory / "transcripts").mkdir()
    report = {"schema_version": 1, "run_id": run_id, "started_at": utc_now(), "finished_at": None,
              "engine_version": __version__, "python_version": sys.version.split()[0],
              "minecraft_version": targets["minecraft_version"], "state": "running", "complete": False,
              "repeat": repeat, "normalization": NORMALIZATION,
              "targets": {name: {"host": t["host"], "port": t["port"]} for name, t in targets["targets"].items()},
              "results": [{"id": s["id"], "title": s["title"], "category": s["category"],
                           "status": "error", "observations": {name: [] for name in TARGET_NAMES},
                           "reason": "Not run", "duration_seconds": 0.0, "attempts": [],
                           "flaky": False, "confirmed_mismatch": False} for s in scenarios]}

    def save():
        _update_summary(report)
        atomic_json(directory / "report.json", report)

    save()
    transcripts = {}
    current = None
    start = None
    try:
        with interruption_signals(), process_lock(lock_path, lock_timeout):
            for scenario in scenarios:
                atomic_json(directory / "scenarios" / (scenario["id"] + ".json"), scenario)
            for name in TARGET_NAMES:
                transcripts[name] = Transcript(directory / "transcripts" / (name + ".jsonl"))
            for scenario, current in zip(scenarios, report["results"]):
                start = time.monotonic()
                current["reason"] = "Running; no verdict yet"
                save()
                for number in range(1, repeat + 1):
                    attempt = {"repeat": number, "targets": {}}
                    # Append first to preserve partial attempts on interruption.
                    current["attempts"].append(attempt)
                    for name in TARGET_NAMES:
                        record = _target_record()
                        attempt["targets"][name] = record
                        _attempt_target(scenario, targets["targets"][name], name,
                            number, transcripts[name], client_factory, timeout, record)
                    attempt.update(compare_attempt(attempt["targets"]))
                    save()
                summarize_result(current)
                current["duration_seconds"] = round(time.monotonic() - start, 6)
                save()
            report["complete"] = True
            report["state"] = "finished"
    except (Exception, KeyboardInterrupt) as exc:
        # Catch unexpected engine exceptions too: the artifact is explicitly an
        # infrastructure failure with its type, never a fabricated parity pass.
        report["state"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        report["error"] = {"kind": type(exc).__name__, "reason": str(exc)}
        if current is not None:
            current["status"] = "error"
            current["confirmed_mismatch"] = False
            current["reason"] = "Interrupted" if isinstance(exc, KeyboardInterrupt) else "Engine/infrastructure failure"
            current["duration_seconds"] = round(time.monotonic() - start, 6)
            if current["attempts"]:
                current["observations"] = {name: [o["raw"] for o in current["attempts"][0]["targets"].get(name, {}).get("observations", [])]
                                           for name in TARGET_NAMES}
        # Completed attempts survive; partial attempt shape remains documented.
    finally:
        for transcript in transcripts.values():
            transcript.close()
        report["finished_at"] = utc_now()
        save()
    code = 2 if not report["complete"] or report["summary"]["error"] else (1 if report["summary"]["different"] else 0)
    return directory, report, code
