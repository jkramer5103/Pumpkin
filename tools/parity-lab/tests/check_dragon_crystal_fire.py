"""Check a bounded End crystal fire comparison captured by the existing arena tools."""
import argparse
import json
import re
from pathlib import Path


def check(report, fixture):
    assert report["complete"] and report["client_alive"]
    assert report["cleanup_passed"] and report["stopped"]
    assert [r["name"] for r in report["rows"]] == list(fixture["cases"])
    mismatches = []
    checks = 0
    for row in report["rows"]:
        assert row["expected"] == fixture["cases"][row["name"]]
        for key in ["present", "removed", "after_removal_air"]:
            assert "Test passed" in row[key], (row["name"], key, row[key])
        assert row["player_present"] and "[" in row["pos"]
        assert len(row["samples"]) == fixture["repetitions"]
        for sample in row["samples"]:
            for key in ["before", "base", "present"]:
                assert "Test passed" in sample[key], (row["name"], key, sample[key])
            clock = lambda k: int(re.search(r"The game time is (\d+)", sample[k])[1])
            assert clock("clock_after") - clock("clock_before") == fixture["ticks_per_repetition"]
            checks += 1
            if "Test passed" not in sample["expected"]:
                mismatches.append(row["name"])
                assert "Test passed" in sample["air"]
    for event in report["events"]:
        assert not any(s in event["raw"] for s in ["Unknown or incomplete", "Incorrect argument", "Exception", "panic"]), event
    return {"samples": checks, "mismatches": mismatches, "controls_passed": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--allow-baseline-mismatch", action="store_true")
    args = parser.parse_args()
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/dragon-crystal-fire/cases.json").read_text())
    result = check(json.loads(args.report.read_text()), fixture)
    print(json.dumps(result, indent=2))
    if not args.allow_baseline_mismatch:
        assert not result["mismatches"], result
