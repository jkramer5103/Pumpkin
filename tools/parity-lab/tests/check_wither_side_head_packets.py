"""Check raw headless-client packets from the bounded two-victim Wither arena.

Run with a report.json containing rows of one-tick packet windows. See
docs/wither-side-head-firing-slots.md for the arena and capture procedure.
"""

import json
import math
import re
import sys


def check_report(report):
    assert report["complete"] and report["stopped"], "Incomplete arena run"
    comparisons = []
    distinct_trials = 0
    for row in report["rows"]:
        for name, passed in row["checks"].items():
            if name != "slot_correspondence":
                assert passed, (row["trial"], name)
        boss = None
        victims = {}
        slots = {}
        observed = set()
        for window in row["ticks"]:
            previous_slots = dict(slots)
            for packet in window["packets"]:
                detail = packet["detail"]
                if packet["packet"] == "ClientboundSetEntityDataPacket":
                    if re.search(r"entityId=" + str(boss) + r"\b", detail):
                        for index, value in re.findall(
                            r"EntityMetadata\(id=(17|18), type=[^,]+, value=(\d+)\)",
                            detail,
                        ):
                            slots[int(index) - 16] = int(value)
                    continue
                if packet["packet"] != "ClientboundAddEntityPacket":
                    continue
                entity_id = int(re.search(r"entityId=(\d+)", detail)[1])
                if "type=WITHER," in detail:
                    boss = entity_id
                if "type=SHEEP," in detail:
                    victims[entity_id] = [
                        float(re.search(r"\b" + axis + r"=([-+\d.Ee]+)", detail)[1])
                        for axis in "xz"
                    ]
                if "type=WITHER_SKULL," not in detail:
                    continue
                x, y, z = [
                    float(re.search(r"\b" + axis + r"=([-+\d.Ee]+)", detail)[1])
                    for axis in "xyz"
                ]
                if math.hypot(x - 8, z - 3) < 0.2:
                    continue  # Main head is outside this regression's scope.
                assert abs(y - 82.2) < 0.04 and abs(x - 8) > 0.8
                if len(previous_slots) != 2 or previous_slots[1] == previous_slots[2]:
                    continue  # Equal targets cannot distinguish the two slots.
                assert set(previous_slots.values()) <= set(victims)
                vx, _, vz = map(
                    float, re.search(r"movement=\(([^)]+)\)", detail)[1].split(",")
                )
                scores = {
                    eid: ((tx - x) * vx + (tz - z) * vz)
                    / (math.hypot(tx - x, tz - z) * math.hypot(vx, vz))
                    for eid, (tx, tz) in victims.items()
                }
                aimed = max(scores, key=scores.get)
                assert scores[aimed] > 0.999, scores
                assert max(scores.values()) - min(scores.values()) > 0.05, scores
                slot = 1 if x < 8 else 2
                observed.add(slot)
                comparisons.append(
                    (row["trial"], window["tick"], slot, previous_slots[slot], aimed)
                )
        distinct_trials += observed == {1, 2}
    assert distinct_trials >= 2, "Need two trials with different side-head targets"
    failures = [item for item in comparisons if item[3] != item[4]]
    assert not failures, ("Wrong side-head firing slot", failures)
    return {"distinct_trials": distinct_trials, "matching_shots": len(comparisons)}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as source:
        print(json.dumps(check_report(json.load(source))))
