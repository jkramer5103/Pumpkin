# Engine usage and evidence

Run from the project root. The runtime has no third-party dependencies.

```sh
python3 -m lab list --scenarios scenarios
python3 -m lab run --targets runtime/targets.json --scenarios scenarios --output artifacts/runs
python3 -m lab run --targets runtime/targets.json --scenarios scenarios --output artifacts/runs --id stone-placement --repeat 2
python3 -m lab run --targets runtime/targets.json --id stone-placement --id positioned-relative --repeat 2
python3 -m lab shrink --targets runtime/targets.json --scenario scenarios/stone-placement.json --output artifacts/shrinks --repeat 2
python3 -m unittest discover -s tests -p 'test_core*.py' -v
```

`list` prints an object containing `schema_version` and a `scenarios` array.
`run` and `shrink` print their artifact directory. `--timeout` bounds each RCON
operation (default 10 seconds). `run --lock-timeout` bounds the process-lock wait
(default 30 seconds). The global lock is independent of the output directory.
Repeat `run --id` to select several scenarios. Every requested ID must exist;
unknown IDs fail validation before either server is contacted.

Run exits: 0 means every selected scenario passed, 1 means an expectation failure,
output difference, capability gap or flaky outcome, and 2 means infrastructure,
validation or interruption failure. Infrastructure errors take precedence over
differences. Invalid configuration is rejected before any connection and reported
on stderr; it does not create a run. A valid run creates `report.json`, scenario
copies, and per-target JSONL transcripts. Reports are replaced atomically with
file and directory fsync. Requests are durably logged before execution. Ctrl-C
and SIGTERM attempt cleanup and finalize an incomplete error report. A hard kill
may leave `state=running`, `complete=false`; never treat that as a successful run.

The contract report fields are retained. Additional fields include:

- `attempts`: all repeats, both targets, setup/steps/cleanup/timing commands,
  raw responses, normalized observations, expectation results and errors.
- `observations`: the first repeat's raw observations, for contract consumers.
  Subsequent repeats remain in `attempts` and the transcripts.
- `flaky`: observations or outcomes differed across repeats. Equal outputs on
  both targets can still be flaky if both change between repeats.
- `confirmed_mismatch`: at least two stable repeats with differing observations,
  passing vanilla positive assertions, no unsupported command and no infrastructure
  error. Single-repeat differences, failing vanilla oracles, equal expectation
  failures, flakes and capability gaps are not confirmed.
- `unsupported_commands` and `command_coverage`: command rejection evidence and
  response counts. Rejected syntax can also appear as `unsupported`; inspect the
  command and raw response before concluding a feature is unimplemented.
- `complete`, `state`, and run metadata: completion must be checked alongside
  the summary. Not-yet-run scenarios start with error status, never pass status.

Normalization removes only `[Rcon] `, `[RCON] ` and `[Server] ` wrappers at the
start of each line, optionally preceded by `[Not Secure] `. It preserves all
other case, whitespace, coordinates, counts, ordering, UUIDs, formatting and NBT.
Known sender prefixes are interpreted the same way for chat, terminal execute
probes and error classification. Raw output is never normalized in evidence.
`response_packets_hex` also preserves the original command response packet bodies.
Transport failures preserve received command wire bytes, including incomplete
frames, without capturing authentication traffic. No target password is copied
into reports, scenario snapshots or transport diagnostics.

Each repeat reruns setup and cleanup independently on vanilla, then Pumpkin.
Every scenario needs an observed step with a nonempty `expect_contains`; that
expectation is checked on both targets after prefix normalization. Empty observed
responses and recognized failed probes cannot pass even if both outputs agree.
Command rejection is visible in any phase. An already-empty `kill` during arena
setup/cleanup is treated as idempotent; its raw response remains in evidence.
Unloaded positions and internal command execution errors are infrastructure
failures, because the intended world precondition or observation is unavailable.
An infrastructure verdict retains concurrent command rejections, failed positive
assertions and response mismatches in the attempt's `failures` array. Infrastructure
entries use `kind=infrastructure_error` with the original target error attached;
exit code 2 still takes precedence.

`wait_ticks` advances simulation **after** its command. Such scenarios run frozen,
use `tick step N`, and poll `time query gametime` until exactly N simulation ticks
have elapsed. Known vanilla 26.3 and Pumpkin game-time response grammars are
parsed for this barrier, without normalizing their raw responses. Existing frozen
state is retained; a running server is restored even after a cleanup transport
failure when a new authenticated connection can be established. Unsupported
timing commands or unrecognized state/time replies are visible capability gaps;
there is no wall-clock simulation fallback.

Shrinking delta-debugs ordered **steps**, retaining setup, cleanup and metadata.
Each valid candidate runs against both targets with at least two repeats and
preserved evidence. A stable failure identity must match the initial failure;
infra, unsupported commands and flaky candidates cannot produce a minimized claim.
The algorithm checks single-step deletion minimality and reruns the final
reproducer on both targets before writing `reproducer.json` and `minimized=true`.
This is 1-minimality among valid step subsequences, not a globally shortest
scenario. A probe budget failure leaves `minimized=false` and all evidence.

This engine observes RCON command behavior only. It does not implement clients or
claim movement, inventory, rendering or general gameplay coverage. Schema
validation checks the shared JSON structure, not the full Minecraft command
grammar or arbitrary command coordinate bounds. Scenarios must follow the arena
contract. RCON framing uses a short standard English `list` response as its
read-only fence after the first response packet; nonstandard or oversized fences
are explicit protocol errors. The provisioned clientless servers cap players at
two. Report persistence cannot be guaranteed if the output storage itself fails.

The live campaign checked upstream `5b53f064` as well as the older released
candidate. That upstream revision has no RCON implementation or configuration;
its successful build and boot do not establish RCON readiness. The provisioning
lane restored the release after that readiness check failed. A catalog run on
the restored candidate therefore validates the release, not a source patch.
Missing RCON remains an infrastructure failure. Separate scratch-console probes
can establish targeted source behavior, but do not establish full RCON catalog
parity. Current upstream also rejects terminal `execute if entity` assertions;
that command rejection is a separate capability gap from the absent transport.
