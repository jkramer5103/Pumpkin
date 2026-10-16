"""The contract CLI. stdout is catalog JSON or the artifact directory path."""

import argparse
import json
import sys

from .runner import run
from .rcon import RconError
from .schema import SchemaError, load_scenarios, load_targets, read_json
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
    execute.add_argument("--order", choices=("alternating", "sorted", "shuffle"), default="alternating",
                         help="scenario order in each suite-wide trial (default alternates forward/reverse)")
    execute.add_argument("--order-seed", type=int, default=0, help="local shuffle seed; recorded with full schedule")
    execute.add_argument("--reset", help='JSON {"commands": [...]} reset before each target/trial')
    execute.add_argument("--versions", help="allowlisted declared versions, local binary hashes and optional world directory identities")
    execute.add_argument("--probe-ticks", action="store_true", help="verify freeze/step with a game-time barrier on both targets")
    execute.add_argument("--pumpkin-console", help="explicit current-source scratch console binary; not RCON")
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
    fuzz = commands.add_parser("fuzz", help="finite seeded arithmetic/block differential fuzzing with reduction")
    fuzz.add_argument("--targets", required=True)
    fuzz.add_argument("--versions", required=True)
    fuzz.add_argument("--output", default="artifacts/fuzz")
    fuzz.add_argument("--seed", type=int, required=True)
    fuzz.add_argument("--seeds", type=_positive_int, default=10)
    fuzz.add_argument("--actions", type=_positive_int, default=12)
    fuzz.add_argument("--mode", choices=("mixed", "scoreboard", "blocks"), default="mixed")
    fuzz.add_argument("--max-seconds", type=float, default=300)
    fuzz.add_argument("--max-probes", type=_positive_int, default=30)
    fuzz.add_argument("--timeout", type=_timeout, default=3)
    fuzz.add_argument("--lock-timeout", type=_timeout, default=10)
    fuzz.add_argument("--pumpkin-console")
    replay = commands.add_parser("replay", help="rerun a saved reproducer with its reset and transport policy")
    replay.add_argument("--reproducer", required=True)
    replay.add_argument("--targets", required=True)
    replay.add_argument("--output")
    replay.add_argument("--timeout", type=_timeout)
    replay.add_argument("--lock-timeout", type=_timeout)
    recover = commands.add_parser("recover", help="finalize an abandoned run under the shared lock; never replay commands")
    recover.add_argument("--run", required=True, dest="run_directory")
    recover.add_argument("--lock-timeout", type=_timeout, default=30.0)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.action == "list":
            scenarios = load_scenarios(args.scenarios)
            print(json.dumps({"schema_version": 1, "scenarios": scenarios}, ensure_ascii=False, indent=2))
            return 0
        if args.action == "recover":
            from .recovery import recover_run
            directory, report, code = recover_run(args.run_directory, lock_timeout=args.lock_timeout)
        elif args.action == "fuzz":
            from .fuzz import fuzz
            directory, report, code = fuzz(args.targets, args.output, seed=args.seed, seeds=args.seeds,
                actions=args.actions, mode=args.mode, max_seconds=args.max_seconds, max_probes=args.max_probes,
                timeout=args.timeout, lock_timeout=args.lock_timeout, versions_path=args.versions,
                pumpkin_console=args.pumpkin_console)
        elif args.action == "shrink":
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
            reset = read_json(args.reset) if args.reset else {"commands": []}
            if set(reset) != {"commands"} or not isinstance(reset["commands"], list):
                raise SchemaError('reset must contain only a commands array')
            directory, report, code = run(scenarios, targets, args.output, repeat=args.repeat,
                timeout=args.timeout, lock_timeout=args.lock_timeout, reset_commands=reset["commands"],
                order=args.order, order_seed=args.order_seed, probe_ticks=args.probe_ticks,
                pumpkin_console=args.pumpkin_console,
                target_versions=read_json(args.versions) if args.versions else None)
        print(directory)
        if code == 2:
            print("Infrastructure/validation failure or incomplete run; inspect the report and transcripts.", file=sys.stderr)
        return code
    except (SchemaError, ShrinkError, RconError, OSError, ValueError) as exc:
        print(f"lab: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("lab: interrupted before a run could be recorded", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
