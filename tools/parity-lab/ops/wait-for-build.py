"""Let a worker checkpoint instead of spending inference polling a compiler."""
import argparse
import re
from pathlib import Path
from common import ACCOUNTS, RUNTIME, atomic_json, utc

parser = argparse.ArgumentParser()
parser.add_argument("--account", required=True, choices=list(ACCOUNTS))
parser.add_argument("--unit", required=True)
parser.add_argument("--reason", required=True)
args = parser.parse_args()
if not re.fullmatch(r"pumpkin-parity-[A-Za-z0-9_.-]+\.scope", args.unit):
    parser.error("Only lab build/test scopes are valid dependencies")
atomic_json(RUNTIME / "worker-waits" / f"{args.account}.json", {
    "unit": args.unit, "reason": args.reason, "requested_at": utc()})
print("Checkpoint recorded. End this turn; the supervisor will resume it after the scope exits.")
