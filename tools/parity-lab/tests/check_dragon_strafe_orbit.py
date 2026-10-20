"""Check observed flight responses when a dragon chooses a new strafe orbit."""
import argparse
import hashlib
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).parents[1] / "fixtures/dragon-strafe-orbit/cases.json"


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
    assert len(item["attempts"]) == fixture["trials"]
    failures = []
    stimuli = []
    count = 0
    for trial, row in enumerate(item["attempts"], 1):
        assert row["trial"] == trial
        assert row["checks"]["acquired_target"]
        assert row["checks"]["completed_approach"]
        assert row["checks"]["client_present"]
        assert row["checks"]["matched_node_columns"]
        assert [(r["x"], r["z"]) for r in row["terrain"]] == [tuple(p) for p in fixture["flight_node_columns"]]
        assert all("Test passed" in r["raw"] for r in row["terrain"])
        assert "Test passed" in row["cleanup"]
        assert not any(any(t in e["raw"] for t in ("not loaded", "Incorrect argument", "Unknown command")) for e in row["events"])
        cases = [case for case in fixture["cases"] for _ in range(fixture["repeats"])]
        assert len(row["samples"]) == len(cases)
        cases.append({"id": "no_ai", "z": 30.0, "y": 140.0, "dy": 0.0})
        for index, (sample, case) in enumerate(zip(row["samples"] + [row["no_ai_control"]], cases)):
            before = sample["before"]
            assert (sample["y"], sample["z"]) == (140.0, case["z"])
            assert vector(before["Pos"]) == [8.0, 140.0, case["z"]]
            assert vector(before["Motion"]) == [0.0, 0.0, 0.0]
            yaw, pitch = vector(before["Rotation"])
            assert abs(yaw) == 180.0 and pitch == 0.0
            assert vector(before["player"]) == [8.0, 140.0, 0.0]
            assert scalar(before["player_health"]) == 20
            assert "Test passed" in before["air"]
            assert scalar(before["DragonPhase"]) == scalar(sample["phase"]) == 1
            no_ai = before["NoAI"]
            if case["id"] == "no_ai":
                assert scalar(no_ai) == 1
                assert vector(sample["position"]) == vector(before["Pos"])
                assert vector(sample["motion"]) == [0.0, 0.0, 0.0]
            else:
                assert no_ai.strip() == "Found no elements matching NoAI" or scalar(no_ai) == 0
                assert abs(vector(sample["position"])[2] - case["z"]) > 0.001
            clock = lambda raw: int(re.search(r"\d+", raw)[0])
            assert clock(sample["clock"]) - clock(before["clock"]) == 1
            actual_y = vector(sample["position"])[1]
            actual_dy = vector(sample["motion"])[1]
            count += 1
            if abs(actual_y - case["y"]) > 1e-9 or abs(actual_dy - case["dy"]) > 1e-11:
                failures.append({"trial": trial, "sample": index, "case": case["id"], "y": actual_y, "dy": actual_dy})
        events = row["events"][row["controlled_start"]:row["controlled_end"]]
        # Read-only clock polling varies with response timing; tick deltas are checked above.
        stimuli.append([event["command"] for event in events if event["command"] != "time query gametime"])
    if target == "baseline":
        expected = [(trial, index) for trial in range(1, fixture["trials"] + 1) for index in range(fixture["repeats"], 3 * fixture["repeats"])]
        assert [(f["trial"], f["sample"]) for f in failures] == expected, failures
        assert all(f["y"] > 139.998 and f["dy"] > -0.001 for f in failures)
    else:
        assert not failures, failures
    return {"target": target, "cases": count, "passed": count - len(failures), "failures": failures, "controlled_ticks": count, "stimulus_sha256": hashlib.sha256(json.dumps(stimuli, sort_keys=True).encode()).hexdigest(), "binary_sha256": item.get("sha256")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("target", choices=["vanilla", "baseline", "fixed"])
    args = parser.parse_args()
    print(json.dumps(check(args.report, args.target), indent=2))
