#!/usr/bin/env python3
"""Run opt-in simulation cases with verified tick barriers and scratch chunk loading."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from infra.catalog import validate_catalog
from lab.runner import run
from lab.schema import load_scenarios, load_targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, default=ROOT/'runtime/targets.json')
    parser.add_argument('--scenarios', type=Path, default=ROOT/'scenarios/simulation')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/simulation')
    parser.add_argument('--id', action='append')
    parser.add_argument('--repeat', type=int, default=2)
    parser.add_argument('--timeout', type=float, default=4)
    parser.add_argument('--lock-timeout', type=float, default=10)
    parser.add_argument('--pumpkin-console', type=Path,
                        help='Explicit source binary; fresh private chunk fixture, not RCON')
    args = parser.parse_args(argv)
    if not 1 <= args.repeat <= 5 or not 0 < args.timeout <= 10 or not 0 < args.lock_timeout <= 30:
        parser.error('repeat must be 1..5, timeout >0 and <=10, lock-timeout >0 and <=30')
    scenarios = validate_catalog(load_scenarios(args.scenarios, args.id))
    for scenario in scenarios:
        waits = [s.get('wait_ticks', 0) for s in scenario['steps']]
        if not any(waits) or sum(waits) > 40:
            parser.error(f"{scenario['id']}: simulation case needs 1..40 total verified ticks")
    directory, _, code = run(scenarios, load_targets(args.targets), args.output,
                            repeat=args.repeat, timeout=args.timeout, lock_timeout=args.lock_timeout,
                            probe_ticks=True, pumpkin_console=args.pumpkin_console,
                            console_arena=args.pumpkin_console is not None)
    print(directory)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
