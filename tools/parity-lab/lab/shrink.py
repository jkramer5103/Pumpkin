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
from pathlib import Path

from .runner import atomic_json, run
from .schema import SchemaError, load_targets, read_json, validate_scenario


class ShrinkError(ValueError):
    pass


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
    if result["status"] != "different" or result.get("flaky") or result.get("repeat_count", 0) < 2:
        return None
    attempts = result["attempts"]
    if any(not t["completed"] or t["errors"] for a in attempts for t in a["targets"].values()):
        return None
    if any(f["kind"] == "unsupported" for a in attempts for f in a["failures"]):
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
            identity.append(("observation_mismatch", "both", vanilla["command"], ""))
    return sorted(set(identity)) or None


def shrink_scenario(scenario_path, targets_path, output, *, repeat=2, timeout=10.0, max_probes=100):
    if repeat < 2:
        raise ShrinkError("Scenario shrinking requires at least two repeats per candidate")
    if max_probes < 2:
        raise ShrinkError("max_probes must be at least 2")
    original = validate_scenario(read_json(scenario_path), str(scenario_path))
    targets = load_targets(targets_path)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # A unique session directory avoids overwriting previous reproducers.
    import tempfile
    directory = Path(tempfile.mkdtemp(prefix="shrink-", dir=output))
    state = {"schema_version": 1, "state": "running", "minimized": False,
             "minimality": None, "original_step_count": len(original["steps"]), "probes": []}
    atomic_json(directory / "original.json", original)

    def save():
        atomic_json(directory / "shrink-report.json", state)

    baseline = None

    def predicate(indices):
        nonlocal baseline
        scenario = copy.deepcopy(original)
        scenario["steps"] = [original["steps"][i] for i in indices]
        try:
            validate_scenario(scenario)
        except SchemaError:
            return False
        if len(state["probes"]) >= max_probes:
            raise ShrinkError("Probe budget exhausted; no minimized claim")
        run_dir, report, code = run([scenario], targets, directory / "runs", repeat=repeat, timeout=timeout)
        result = report["results"][0]
        identity = failure_identity(result)
        state["probes"].append({"indices": list(indices), "run": str(run_dir), "exit_code": code,
                                "failure_identity": identity})
        save()
        if code == 2:
            raise ShrinkError("Infrastructure failure during shrinking; evidence preserved")
        if result.get("flaky"):
            raise ShrinkError("Flaky candidate encountered; no minimized claim")
        if baseline is None:
            if identity is None:
                raise ShrinkError("Initial scenario lacks a stable supported behavioral failure")
            baseline = identity
        return identity == baseline

    save()
    try:
        indices = ddmin(range(len(original["steps"])), predicate)
        reproducer = copy.deepcopy(original)
        reproducer["steps"] = [original["steps"][i] for i in indices]
        atomic_json(directory / "reproducer.json", reproducer)
        state.update(state="finished", minimized=True, minimality="1-minimal subsequence of steps",
                     retained_indices=indices, step_count=len(indices),
                     verified_run=state["probes"][-1]["run"],
                     limitations="Setup and cleanup are retained. 1-minimal does not mean globally shortest.")
    except (Exception, KeyboardInterrupt) as exc:
        state.update(state="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                     error={"kind": type(exc).__name__, "reason": str(exc)})
    finally:
        save()
    return directory, state, 0 if state["minimized"] else 2
