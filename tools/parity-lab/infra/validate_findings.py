#!/usr/bin/env python3
"""Replay focused findings with the engine lock and explicit scratch-console arena."""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from infra.catalog import validate_catalog
from lab.runner import atomic_json, run
from lab.schema import load_scenarios, load_targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, default=ROOT/'runtime/targets.json')
    parser.add_argument('--pumpkin-console', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/findings')
    parser.add_argument('--id', action='append')
    args = parser.parse_args(argv)
    cases = load_scenarios(ROOT/'scenarios/findings') + load_scenarios(ROOT/'scenarios/simulation')
    if args.id:
        missing = set(args.id) - {case['id'] for case in cases}
        if missing:
            parser.error('Unknown finding IDs: ' + ', '.join(sorted(missing)))
        cases = [case for case in cases if case['id'] in args.id]
    validate_catalog(cases)
    with args.pumpkin_console.open('rb') as binary:
        digest = hashlib.file_digest(binary, 'sha256').hexdigest()
    directory, _, code = run(cases, load_targets(args.targets), args.output,
                            repeat=2, timeout=5, lock_timeout=30,
                            probe_ticks=any(s.get('wait_ticks') for c in cases for s in c['steps']),
                            pumpkin_console=args.pumpkin_console, console_arena=True)
    atomic_json(directory/'binary.json', {'path': str(args.pumpkin_console.resolve()), 'sha256': digest})
    print(directory)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
