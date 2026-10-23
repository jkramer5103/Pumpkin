"""Compare the bounded dragon-fireball arena reports against official 26.3."""
import argparse
import json
import re
from pathlib import Path


def vector(raw):
    match = re.search(r"\[([^\[\]]+)\]\s*$", raw)
    return tuple(float(part.strip().rstrip("d")) for part in match[1].split(",")) if match else None


def check(reference, candidate):
    failures = []
    for name, report in [("reference", reference), ("candidate", candidate)]:
        assert report["complete"] and report["stopped"], name
        assert report["cleanup"] and report["client_alive"], name
        assert len(report["rows"]) == 14, name
        assert all(row["client_present"] for row in report["rows"]), name
    assert reference["probe_sha256"] == candidate["probe_sha256"]
    checks = 0
    for expected, actual in zip(reference["rows"], candidate["rows"]):
        assert (actual["trial"], actual["name"]) == (expected["trial"], expected["name"])
        assert len(actual["samples"]) == len(expected["samples"]) == 10
        for report, row in [(reference, expected), (candidate, actual)]:
            assert row["present"].startswith("Test passed")
            events = report["events"][row["events_start"]:row["events_end"]]
            assert not any(any(error in event["raw"] for error in ["not loaded", "Unknown or incomplete command", "Incorrect argument"]) for event in events)
        # Setup readiness and TickController's read-only settlement polls may vary.
        def commands(report, row):
            return [event["command"] for event in report["events"][row["events_start"]:row["events_end"]] if event["command"] != "time query gametime"]
        assert commands(reference, expected) == commands(candidate, actual)
        for row in [expected, actual]:
            clocks = [int(re.search(r"\d+", sample["clock"])[0]) for sample in row["samples"]]
            assert all(b-a == 1 for a, b in zip(clocks, clocks[1:]))
        for oracle, sample in zip(expected["samples"], actual["samples"]):
            assert oracle["tick"] == sample["tick"]
            for field in ["ball", "cloud", "pos", "motion", "cloud_pos"]:
                if field in ["ball", "cloud"]:
                    agrees = sample[field].startswith("Test passed") == oracle[field].startswith("Test passed")
                else:
                    result, wanted = vector(sample[field]), vector(oracle[field])
                    agrees = result is None if wanted is None else result is not None and max(abs(x-y) for x, y in zip(result, wanted)) < 1e-8
                checks += 1
                if not agrees:
                    failures.append({"trial": actual["trial"], "case": actual["name"], "tick": sample["tick"], "field": field, "actual": sample[field], "expected": oracle[field]})
    return {"checks": checks, "passed": checks - len(failures), "failures": failures}


def check_strafe(report, target):
    assert report["complete"]
    item = report["targets"][target]
    assert item["stopped"] and len(item["attempts"]) == 2
    failures = []
    checks = 0
    for row in item["attempts"]:
        assert all(row["checks"].values()) and row["cleanup"].startswith("Test passed")
        assert row["first_attack"] == 5
        observations = [("launch", row["projectile_at_shot"].startswith("Test passed")),
                        ("no_immediate_cloud", row["cloud_at_shot"].startswith("Test passed"))]
        positions = [vector(row["projectile_pos"])] + [vector(sample["pos"]) for sample in row["flight"]]
        observations += [("travel_" + str(i), a is not None and b is not None and sum((x-y)**2 for x, y in zip(a, b)) > 0.001)
                         for i, (a, b) in enumerate(zip(positions, positions[1:]))]
        for name, agrees in observations:
            checks += 1
            if not agrees:
                failures.append({"trial": row["trial"], "field": name})
    return {"checks": checks, "passed": checks - len(failures), "failures": failures}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.reference.read_text()), json.loads(args.candidate.read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["failures"]))
