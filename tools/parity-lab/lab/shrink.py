"""Delta debugging, with real two-server reruns for scenario reproducers.

ddmin is also usable independently with a deterministic predicate. It checks
the initial failure, verifies single-deletion minimality, and reruns the final
sequence. An unstable final predicate raises instead of claiming minimization.
Scenario shrinking preserves metadata/setup/cleanup and removes only steps.
Every candidate is a full locked engine run with evidence; positive observation
validation and stable failure identity are required. No server is mocked here.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shlex
import sys
import tempfile
from pathlib import Path

from .runner import atomic_json, interruption_signals, run, utc_now
from .schema import load_targets, read_json, validate_scenario
from .provenance import ProvenanceError, check_transports, verify_versions


class ShrinkError(ValueError):
    pass


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _replay_policy(state):
    return {key: state.get(key) for key in ('repeat', 'timeout', 'lock_timeout',
                                           'pumpkin_console', 'console_arena')}


def ddmin(sequence, fails):
    """Return a 1-minimal failing subsequence (not necessarily a global minimum).

    fails must be a deterministic callable. No caching: the final verification
    really executes the predicate again. Input ordering is always preserved.
    """
    current = list(sequence)
    if not fails(current):
        raise ShrinkError("Initial sequence does not reproduce the failure")
    if not current:
        if not fails(current):
            raise ShrinkError("Failure became unstable during final verification")
        return current
    granularity = 2
    while current:
        width = (len(current) + granularity - 1) // granularity
        reduced = False
        if len(current) > 1:
            for start in range(0, len(current), width):
                candidate = current[start:start + width]
                if len(candidate) < len(current) and fails(candidate):
                    current = candidate
                    granularity = 2
                    reduced = True
                    break
        if reduced:
            continue
        for start in range(0, len(current), width):
            candidate = current[:start] + current[start + width:]
            if fails(candidate):
                current = candidate
                granularity = max(2, granularity - 1)
                reduced = True
                break
        if not reduced:
            if granularity >= len(current):
                break
            granularity = min(len(current), granularity * 2)
    # Explicitly verify 1-minimality, including non-monotonic predicates.
    index = 0
    while index < len(current):
        candidate = current[:index] + current[index + 1:]
        if fails(candidate):
            current = candidate
            index = 0
        else:
            index += 1
    if not fails(current):
        raise ShrinkError("Failure became unstable during final verification")
    return current


def failure_identity(result):
    """Stable behavioral failure identity; infra, flaky, unsupported are rejected."""
    if not result.get("confirmed_mismatch") or result.get("flaky") or result.get("repeat_count", 0) < 2:
        return None
    attempts = result["attempts"]
    if any(not t["completed"] or t["errors"] for a in attempts for t in a["targets"].values()):
        return None
    if any(f["kind"] == "unsupported" for a in attempts for f in a["failures"]):
        return None
    # Recheck old saved reports too: earlier runners could confirm differences
    # despite a failed reference setup/action/cleanup.
    if any(f["kind"] in ("expectation_failed", "command_failed") and f.get("target") == "vanilla"
           for a in attempts for f in a["failures"]):
        return None
    identity = []
    first = attempts[0]
    for name, target in first["targets"].items():
        for observation in target["observations"]:
            if observation["expectation_met"] is False:
                identity.append(("expectation_failed", name, observation["command"], observation["expect_contains"]))
        for problem in target["problems"]:
            identity.append((problem["kind"], name, problem.get("command", ""), ""))
    left, right = (first["targets"][name]["observations"] for name in ("vanilla", "pumpkin"))
    for vanilla, pumpkin in zip(left, right):
        if vanilla["normalized"] != pumpkin["normalized"]:
            identity.append(("observation_mismatch", "both", vanilla["command"],
                             vanilla["normalized"], pumpkin["normalized"]))
    return sorted(set(identity), key=repr) or None


def load_reset(path):
    value = read_json(path)
    if set(value) != {"commands"} or not isinstance(value["commands"], list) or not value["commands"]:
        raise ShrinkError('Reset file must contain a nonempty "commands" array')
    # Reuse the command grammar without extending the scenario schema.
    validate_scenario({"schema_version": 1, "id": "reset", "title": "Reset", "category": "reset",
        "description": "Reset validation", "tags": [], "setup": value["commands"], "cleanup": [],
        "steps": [{"command": "say validate", "observe": True, "expect_contains": "validate"}]})
    return value["commands"]


def load_versions(path):
    """Explicit provenance, with local binary hashes verified before execution.

    No arbitrary manifest copying: manifests may contain credentials. Version
    strings are declarations; local hashes establish which file was checked,
    not that an existing remote service is running that file.
    """
    try:
        return verify_versions(read_json(path))
    except ProvenanceError as exc:
        raise ShrinkError(str(exc)) from exc


def _console_version(versions, pumpkin_console):
    try:
        check_transports(versions, pumpkin_console)
    except ProvenanceError as exc:
        raise ShrinkError(str(exc)) from exc


def shrink_scenario(scenario_path, targets_path, output, *, repeat=2, timeout=10.0, max_probes=100,
                    reset_path=None, versions_path=None, keep_steps=(), lock_timeout=30.0,
                    pumpkin_console=None, console_arena=False):
    if repeat < 2:
        raise ShrinkError("Scenario shrinking requires at least two repeats per candidate")
    if max_probes < 2:
        raise ShrinkError("max_probes must be at least 2")
    if reset_path is None or versions_path is None:
        raise ShrinkError("Shrinking requires explicit reset and target versions files")
    original = validate_scenario(read_json(scenario_path), str(scenario_path))
    targets = load_targets(targets_path)
    reset = load_reset(reset_path)
    versions = load_versions(versions_path)
    _console_version(versions, pumpkin_console)
    pinned = set(keep_steps) | {i for i, step in enumerate(original["steps"]) if step.get("observe")}
    if any(type(i) is not int or not 0 <= i < len(original["steps"]) for i in pinned):
        raise ShrinkError("keep-step indices must be valid zero-based step indices")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="shrink-", dir=output))
    state = {"schema_version": 1, "state": "running", "minimized": False,
             "started_at": utc_now(), "finished_at": None, "minimality": None,
             "original_step_count": len(original["steps"]), "probes": [], "pinned_indices": sorted(pinned),
             "target_versions": versions, "repeat": repeat, "timeout": timeout, "console_arena": console_arena,
             "lock_timeout": lock_timeout,
             "pumpkin_console": str(Path(pumpkin_console).resolve()) if pumpkin_console else None,
             "evidence_kind": "live differential comparison; inspect target version declarations",
             "version_limitations": "RCON service binary identity is declared, not remotely attested. Local file hashes are verified."}
    state['replay_integrity'] = {'reset_sha256': _digest(reset),
                                 'policy_sha256': _digest(_replay_policy(state))}
    atomic_json(directory / "original.json", original)
    atomic_json(directory / "reset.json", {"commands": reset})
    atomic_json(directory / "target-versions.json", versions)
    replay_argv = [sys.executable, "-m", "lab", "replay", "--reproducer", str(directory),
                   "--targets", str(Path(targets_path).resolve())]
    state["replay_argv"] = replay_argv
    state["replay_cwd"] = str(Path(__file__).resolve().parents[1])
    state["replay_command"] = "cd " + shlex.quote(state["replay_cwd"]) + " && " + shlex.join(replay_argv)
    (directory / "replay.txt").write_text(state["replay_command"] + "\n", encoding="utf-8")

    def save():
        atomic_json(directory / "shrink-report.json", state)
        atomic_json(directory / "attempts.json", state["probes"])

    baseline = None

    def predicate(removable):
        nonlocal baseline
        indices = sorted(pinned | set(removable))
        scenario = copy.deepcopy(original)
        scenario["steps"] = [original["steps"][i] for i in indices]
        validate_scenario(scenario)
        if len(state["probes"]) >= max_probes:
            raise ShrinkError("Probe budget exhausted; no minimized claim")
        # Detect changed binaries between candidates, rather than silently
        # shrinking across two source versions. Never cache predicate outcomes.
        if load_versions(directory / "target-versions.json") != versions:
            raise ShrinkError("Saved target versions changed during shrinking")
        probe = {"indices": indices, "state": "running", "accepted": False}
        state["probes"].append(probe)
        save()
        run_dir, report, code = run([scenario], targets, directory / "runs", repeat=repeat, timeout=timeout,
            reset_commands=reset, lock_timeout=lock_timeout, pumpkin_console=pumpkin_console,
            console_arena=console_arena, target_versions=versions)
        result = report["results"][0]
        identity = failure_identity(result)
        probe.update(state="finished", run=str(run_dir), exit_code=code, failure_identity=identity)
        save()
        if code == 2:
            raise ShrinkError("Infrastructure failure during shrinking; evidence preserved")
        if result.get("flaky"):
            raise ShrinkError("Flaky candidate encountered; no minimized claim")
        if baseline is None:
            if identity is None:
                raise ShrinkError("Initial scenario lacks a stable supported behavioral mismatch")
            baseline = identity
            state["failure_identity"] = identity
        accepted = identity == baseline
        probe["accepted"] = accepted
        if accepted and len(indices) <= state.get("step_count", len(original["steps"])):
            atomic_json(directory / "candidate.json", scenario)
            state['replay_integrity']['scenario_sha256'] = _digest(scenario)
            state.update(retained_indices=indices, step_count=len(indices), verified_run=str(run_dir))
        save()
        return accepted

    save()
    try:
        with interruption_signals():
            removable = ddmin([i for i in range(len(original["steps"])) if i not in pinned], predicate)
            indices = sorted(pinned | set(removable))
            reproducer = copy.deepcopy(original)
            reproducer["steps"] = [original["steps"][i] for i in indices]
            atomic_json(directory / "reproducer.json", reproducer)
            state.update(state="finished", minimized=True,
                minimality="1-minimal deletion of unpinned steps; all single deletions checked on both targets",
                limitations="Reset, setup, cleanup, observations and explicitly pinned steps are fixed. Not globally shortest.")
    except (Exception, KeyboardInterrupt) as exc:
        state.update(state="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                     error={"kind": type(exc).__name__, "reason": str(exc)})
    finally:
        state["finished_at"] = utc_now()
        save()
    return directory, state, 0 if state["minimized"] else 2


def replay_reproducer(directory, targets_path, *, output=None, timeout=None, lock_timeout=None):
    """Replay the saved candidate, reset policy and transport; never re-shrink."""
    directory = Path(directory).resolve()
    state = read_json(directory / "shrink-report.json")
    versions = load_versions(directory / "target-versions.json")
    if versions != state["target_versions"]:
        raise ShrinkError("Saved target versions differ from the original evidence")
    _console_version(versions, state["pumpkin_console"])
    path = directory / ("reproducer.json" if state["minimized"] else "candidate.json")
    scenario = validate_scenario(read_json(path), str(path))
    reset = load_reset(directory / "reset.json")
    integrity = state.get('replay_integrity')
    if integrity and (integrity.get('scenario_sha256') != _digest(scenario)
                      or integrity.get('reset_sha256') != _digest(reset)
                      or integrity.get('policy_sha256') != _digest(_replay_policy(state))):
        raise ShrinkError('Saved scenario, reset or replay policy differs from the verified evidence')
    return run([scenario], load_targets(targets_path), output or directory / "replays",
        repeat=state["repeat"], timeout=state["timeout"] if timeout is None else timeout,
        lock_timeout=state["lock_timeout"] if lock_timeout is None else lock_timeout,
        reset_commands=reset, pumpkin_console=state["pumpkin_console"],
        console_arena=state.get("console_arena", False), target_versions=versions)
