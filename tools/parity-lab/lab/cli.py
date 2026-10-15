"""The contract CLI. stdout is catalog JSON or the artifact directory path."""

import argparse
import json
import sys

from .runner import run
from .schema import SchemaError, load_scenarios, load_targets
from .shrink import ShrinkError, replay_reproducer, shrink_scenario


def _positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _timeout(value):
    number = float(value)
    if not 0 < number <= 300:
        raise argparse.ArgumentTypeError("must be > 0 and <= 300 seconds")
    return number


def parser():
    root = argparse.ArgumentParser(description="Compare command-observable Minecraft behavior with preserved raw evidence")
    commands = root.add_subparsers(dest="action", required=True)
    catalog = commands.add_parser("list", help="emit validated scenario catalog JSON")
    catalog.add_argument("--scenarios", default="scenarios")
    execute = commands.add_parser("run", help="run both servers serially under the global process lock")
    execute.add_argument("--targets", required=True)
    execute.add_argument("--scenarios", default="scenarios")
    execute.add_argument("--output", default="artifacts/runs")
    execute.add_argument("--id", dest="scenario_id", action="append",
                         help="scenario ID to select; repeat to select multiple scenarios")
    execute.add_argument("--repeat", type=_positive_int, default=1,
                         help="repetitions per scenario; >=2 needed for confirmed mismatch claims")
    execute.add_argument("--timeout", type=_timeout, default=10.0, help="seconds per RCON operation")
    execute.add_argument("--lock-timeout", type=_timeout, default=30.0)
    shrink = commands.add_parser("shrink", help="delta debug steps with real two-server verification and retained evidence")
    shrink.add_argument("--targets", required=True)
    shrink.add_argument("--scenario", required=True)
    shrink.add_argument("--output", default="artifacts/reproducers")
    shrink.add_argument("--repeat", type=_positive_int, default=2)
    shrink.add_argument("--timeout", type=_timeout, default=10.0)
    shrink.add_argument("--max-probes", type=_positive_int, default=100)
    shrink.add_argument("--reset", required=True, help='JSON {"commands": [...]} arena reset before every target/repeat')
    shrink.add_argument("--versions", required=True, help="explicit vanilla/Pumpkin version metadata JSON")
    shrink.add_argument("--keep-step", type=int, action="append", default=[],
                        help="preserve a zero-based step index in addition to all observations")
    shrink.add_argument("--lock-timeout", type=_timeout, default=30.0)
    shrink.add_argument("--pumpkin-console", help="explicit current-source binary; uses a fresh scratch console, not RCON")
    replay = commands.add_parser("replay", help="rerun a saved reproducer with its reset and transport policy")
    replay.add_argument("--reproducer", required=True)
    replay.add_argument("--targets", required=True)
    replay.add_argument("--output")
    replay.add_argument("--timeout", type=_timeout)
    replay.add_argument("--lock-timeout", type=_timeout)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.action == "list":
            scenarios = load_scenarios(args.scenarios)
            print(json.dumps({"schema_version": 1, "scenarios": scenarios}, ensure_ascii=False, indent=2))
            return 0
        if args.action == "shrink":
            directory, report, code = shrink_scenario(args.scenario, args.targets, args.output,
                repeat=args.repeat, timeout=args.timeout, max_probes=args.max_probes,
                reset_path=args.reset, versions_path=args.versions, keep_steps=args.keep_step,
                lock_timeout=args.lock_timeout, pumpkin_console=args.pumpkin_console)
        elif args.action == "replay":
            directory, report, code = replay_reproducer(args.reproducer, args.targets,
                output=args.output, timeout=args.timeout, lock_timeout=args.lock_timeout)
        else:
            targets = load_targets(args.targets)
            scenarios = load_scenarios(args.scenarios, args.scenario_id)
            directory, report, code = run(scenarios, targets, args.output, repeat=args.repeat,
                                         timeout=args.timeout, lock_timeout=args.lock_timeout)
        print(directory)
        if code == 2:
            print("Infrastructure/validation failure or incomplete run; inspect the report and transcripts.", file=sys.stderr)
        return code
    except (SchemaError, ShrinkError, OSError, ValueError) as exc:
        print(f"lab: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("lab: interrupted before a run could be recorded", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
