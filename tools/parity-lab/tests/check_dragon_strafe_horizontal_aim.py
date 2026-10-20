"""Check bounded world regression reports for horizontal dragon strafe aim."""
import argparse
import hashlib
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).parents[1] / "fixtures/dragon-strafe-horizontal-aim/cases.json"


def scalar(raw):
    return float(raw.rsplit(": ", 1)[-1].strip().rstrip("bdfs"))


def vector(raw):
    return [float(x.strip().rstrip("df")) for x in raw.rsplit("[", 1)[-1].strip().removesuffix("]").split(",")]


def check(path, target):
    report = json.loads(Path(path).read_text())
    fixture = json.loads(FIXTURE.read_text())
    assert report["complete"]
    assert report["fixture_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    item = report["targets"][target]
    assert item["stopped"]
    rows = item["attempts"]
    expected = [(trial, case) for trial in range(1, fixture["trials"] + 1) for case in fixture["cases"]]
    assert len(rows) == len(expected)
    failures = []
    stimuli = []
    ticks = 0
    for row, (trial, case) in zip(rows, expected):
        assert (row["trial"], row["case"]) == (trial, case["id"])
        assert all(value for key, value in row["checks"].items() if key != "attack_gate")
        assert scalar(row["phase_before"]) == 1
        assert "Test passed" in row["cleanup"]
        samples = row["samples"]
        assert len(samples) == len(case["covered"])
        phases = []
        for sample, covered in zip(samples, case["covered"]):
            assert sample["covered"] == covered
            before = sample["before"]
            assert vector(before["position"]) == [8.0, case["dragon_y"], 30.0]
            assert vector(before["yaw"]) == [case["yaw"], 0.0]
            assert vector(before["motion"]) == [0.0, 0.0, 0.0]
            assert vector(before["player"]) == [8.0, 80.0, 0.0]
            assert before["no_ai"].strip() == "Found no elements matching NoAI" or scalar(before["no_ai"]) == 0
            assert scalar(before["player_health"]) == 20
            assert "Test passed" in before["wall"]
            clock = lambda raw: int(re.search(r"\d+", raw)[0])
            assert clock(sample["clock_after"]) - clock(before["clock"]) == 1
            ticks += 1
            phase = int(scalar(sample["phase"]))
            assert phase in (0, 1)
            phases.append(phase)
        first = next((i + 1 for i, phase in enumerate(phases) if phase == 0), None)
        assert row["first_attack"] == first
        if first != case["first_attack"]:
            failures.append({"trial": trial, "case": case["id"], "expected": case["first_attack"], "actual": first})
        events = row["events"][row["attack_events_start"]:row["attack_events_end"]]
        stimuli.append([event["command"] for event in events if event["command"].startswith(("tp ", "data merge ", "fill "))])
    if target == "baseline":
        assert [(f["trial"], f["case"]) for f in failures] == [(t, c) for t in (1, 2) for c in ("above", "far_above")], failures
        assert all(f["actual"] is None for f in failures)
    else:
        assert not failures, failures
    return {"target": target, "cases": len(rows), "passed": len(rows) - len(failures), "failures": failures, "controlled_ticks": ticks, "stimulus_sha256": hashlib.sha256(json.dumps(stimuli, sort_keys=True).encode()).hexdigest(), "binary_sha256": item.get("sha256")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("target", choices=["vanilla", "baseline", "fixed"])
    args = parser.parse_args()
    print(json.dumps(check(args.report, args.target), indent=2))
