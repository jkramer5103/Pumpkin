# Engine usage and evidence

Run from the project root. The runtime has no third-party dependencies.

```sh
python3 -m lab list --scenarios scenarios
python3 -m lab run --targets runtime/targets.json --scenarios scenarios --output artifacts/runs
python3 -m lab run --targets runtime/targets.json --scenarios scenarios --output artifacts/runs --id stone-placement --repeat 2
python3 -m lab run --targets runtime/targets.json --id stone-placement --id positioned-relative --repeat 2
python3 -m lab run --targets runtime/targets.json --repeat 3 --order shuffle --order-seed 17 --probe-ticks
python3 -m lab shrink --targets runtime/targets.json --scenario case.json --reset reset.json --versions versions.json --output artifacts/reproducers --repeat 2
python3 -m lab replay --targets runtime/targets.json --reproducer artifacts/reproducers/shrink-SESSION
python3 -m lab recover --run artifacts/runs/RUN_ID
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

Reports also checkpoint each command request and response, observations and target
completion. `pending_command` identifies an in-flight operation; `uncertain_commands`
retains lost/interrupted replies even after cleanup succeeds. Commands with lost
replies may already have mutated the server and are never automatically replayed.
A disconnected scratch console cannot be recreated as a cleanup retry: its session
identity would no longer be proven. Remaining targets/trials still run and retain
the cleanup failure.

`recover --run DIRECTORY` takes the shared engine lock and finalizes a dead owner's
running report as `state=abandoned`, `complete=false`, exit 2. It checks PID, process
start time and host boot ID, including owners still waiting for the engine lock.
It preserves original transcripts, lists requests without a proven response and
records torn transcript lines. Recovery executes no server commands and makes no
cleanup/tick-restoration claim. Inspect uncertainty before further mutations.
Completed/interrupted reports remain unchanged; legacy reports without process
identity cannot be automatically recovered safely.

Ordinary `run` accepts optional `--versions` using the format below. Without it,
`target_versions=null` explicitly means unknown provenance; the Minecraft protocol
version and endpoints alone cannot identify a server build. Scratch binary hashes
are always recorded. Declared binaries/world directories are rechecked after the
lock wait and before each target. Optional `world: {"path": "/absolute/world"}`
records local directory device/inode; subsequent runs/replays check saved identities
and reject replacements. This does not hash world contents, pin seeds, or attest
which world an RCON service has loaded. Scratch attempts record their own world
directory identities when present. Setup/reset/cleanup still do not prove arbitrary
state restoration or general replay determinism.

The contract report fields are retained. Additional fields include:

- `attempts`: all repeats, both targets, setup/steps/cleanup/timing commands,
  raw responses, normalized observations, expectation results and errors.
- `observations`: the first repeat's raw observations, for contract consumers.
  Subsequent repeats remain in `attempts` and the transcripts.
- `flaky`: observations or outcomes differed across repeats. Equal outputs on
  both targets can still be flaky if both change between repeats.
- `confirmed_mismatch`: at least two stable repeats with differing observations,
  passing vanilla positive assertions, no failed vanilla command in any phase,
  no unsupported command and no infrastructure error. Single-repeat differences, failing vanilla oracles, equal expectation
  failures, flakes and capability gaps are not confirmed.
- `unsupported_commands` and `command_coverage`: command rejection evidence and
  response counts. Rejected syntax can also appear as `unsupported`; inspect the
  command and raw response before concluding a feature is unimplemented.
- `complete`, `state`, and run metadata: completion must be checked alongside
  the summary. Not-yet-run scenarios start with error status, never pass status.
- `trial_schedule` records every suite-wide trial's scenario order and zero-based
  position. `trial_details` records completion of the requested series, outcome
  counts, distinct observation/failure outcomes, per-target variability, and a
  classification such as `confirmed_mismatch`, `non_deterministic`,
  `stable_unsupported`, `stable_failure` or `incomplete`.
- `isolation` records the declared reset policy, ordering and seed. It explicitly
  states that arbitrary state restoration is not proven and no world snapshot is
  used. `timing_capabilities` records the optional standalone probe separately
  from scenario verdicts; per-attempt `timing` records verified simulation ticks.

Normalization removes only `[Rcon] `, `[RCON] ` and `[Server] ` wrappers at the
start of each line, optionally preceded by `[Not Secure] `. It preserves all
other case, whitespace, coordinates, counts, ordering, UUIDs, formatting and NBT.
Known sender prefixes are interpreted the same way for chat, terminal execute
probes and error classification. Raw output is never normalized in evidence.
`response_packets_hex` also preserves the original command response packet bodies.
Transport failures preserve received command wire bytes, including incomplete
frames, without capturing authentication traffic. No target password is copied
into reports, scenario snapshots or transport diagnostics.

Each trial runs the entire selected suite, with each scenario's setup and cleanup
on vanilla, then Pumpkin. By default, odd trials use sorted scenario IDs and even
trials reverse that order, exposing some dependencies on earlier tests. `--order
sorted` retains the same order each trial; `--order shuffle --order-seed N` uses
a local seeded generator and records the exact schedule. Ordering is reproducible;
it does not make random gameplay or elapsed time deterministic. A scenario keeps
an error/provisional verdict until every requested trial completes, including when
another scenario interrupts the suite. Duration sums that scenario's own attempts.

`run --reset reset.json` accepts the same commands-array format as shrinking and
executes those commands before setup on each target/trial. A failed reset prevents
candidate execution. Define resets for all state the scenarios share; reversing
order alone neither cleans worlds nor proves order independence. Scratch-console
attempts use fresh Pumpkin worlds; vanilla retains its configured world.

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

`run --probe-ticks` checks each target once under the shared lock before the suite:
query state, freeze if running, request one step, verify exactly one game-time
tick, then restore the previous frozen/running state. Reports preserve every raw
response and report `supported`, `unsupported` or `error`; without the explicit
probe this top-level field stays `untested`, even if individual timing scenarios
have their own evidence. Acknowledging `tick step` without actual advancement is
an error. Probe rejection exits 1 and probe infrastructure failure exits 2, even
when all scenario verdicts pass. Probe commands live in `timing_capabilities` and
transcripts; the existing command-coverage counters describe scenario attempts.
Freeze/step support establishes tick control only, not deterministic entity
iteration, random seeds or broader gameplay simulation.

`run --pumpkin-console /absolute/path/pumpkin` selects the same explicit fresh-world
transport as shrinking. It can be combined with order/reset/timing options and
does not change the configured candidate service or establish upstream RCON support.

Shrinking delta-debugs ordered **unobserved steps**. All observations, setup,
cleanup and metadata are retained. Use repeated `--keep-step N` arguments to pin
additional zero-based step indices. Required behavioral dependencies are retained
when their deletion breaks the original mismatch or a vanilla positive oracle.
Every candidate, including repeated candidates and the final verification, runs
both actual targets at least twice. Nothing uses cached predicate outcomes.

`--reset reset.json` is required and contains `{"commands": ["..."]}`. Write
scenario-specific, idempotent commands that reset every state the scenario
changes, including its arena entities, blocks and scoreboard values. Reset runs
before setup on **each target and each repeat**, under the shared engine lock.
A recognized reset failure aborts that target's candidate and prevents a minimized
claim; cleanup and raw reset evidence remain. Empty entity kills are idempotent.
The engine validates command structure, but cannot prove arbitrary reset commands
restore every state. Use bounded arena commands and split large fills to respect
the server's fill limit. No universal world wipe is inferred.

`--versions versions.json` is required. It contains exactly `vanilla` and
`pumpkin` objects with a nonempty `version`. Optional fields are `source_commit`,
`binary`, `sha256`, `transport` and `world`; arbitrary manifest fields are rejected.
For example:

```json
{
  "vanilla": {"version": "Minecraft Java 26.3", "binary": "/absolute/path/server.jar", "transport": "rcon"},
  "pumpkin": {"version": "upstream COMMIT", "source_commit": "FULL_HASH", "binary": "/absolute/path/pumpkin", "transport": "scratch-console"}
}
```

Local binary SHA-256 values are computed and recorded, then verified again before
every candidate and replay. An explicitly supplied incorrect hash is rejected.
For existing RCON services the version is declared provenance, not remote binary
attestation. Verify deployment against the runtime manifest before making a
current-source claim. Passwords remain in the separate targets file.

Each session under `artifacts/reproducers/` saves `original.json`, the best actually
verified `candidate.json`, `reset.json`, `target-versions.json`, `attempts.json`,
`shrink-report.json`, and an exact `replay.txt` command. Every probe points to its
full run report, scenario snapshot, raw response/packet transcripts and any
scratch console logs. `lab replay` reruns the saved case, reset and transport
policy with two or more repeats; exit 1 means a difference was observed, as with
`lab run`. It does not rerun the shrink algorithm or claim new minimality.
Saved version metadata must still match the original shrink report; editing the
version file cannot silently relabel an old reproducer as a different build.
New shrink sessions also hash the verified candidate, reset and replay policy;
replay refuses edits to those saved inputs before connecting. Existing sessions
without these hashes retain their earlier, limited integrity checks. Explicit
CLI timeout overrides remain possible and do not change saved evidence.

A candidate must preserve the original failure's commands and exact normalized
divergent responses. Infrastructure errors, unsupported commands, flaky repeats
and failed vanilla positive oracles cannot produce a minimized claim. The
algorithm actually checks every remaining unpinned single deletion and reruns the
final case before writing `reproducer.json` and `minimized=true`. This is
1-minimality within those fixed boundaries, not a globally shortest scenario.
`--max-probes` bounds live candidate runs (default 100). Exhaustion or interruption
leaves `minimized=false`, with the best previously verified case still replayable.
The TCP integration demonstrations are explicitly synthetic fixtures, not
Minecraft coverage.

`shrink --pumpkin-console /absolute/path/pumpkin` explicitly enables targeted
source validation when an upstream binary has no RCON. Its path must match the
Pumpkin version record. Every attempt launches and cleanly stops a fresh scratch
world under the engine lock. Networking binds only to an ephemeral loopback port;
plugins, telemetry, LAN broadcast, query and management are disabled. Startup and
shutdown have bounded waits. Console output is retained without prefix or log
stripping. A unique read-only scoreboard lookup fences each command, including
silent conditions; the expected unknown-objective framing lines remain in the
full console log. Reports explicitly identify this as scratch console, and no
current-source RCON coverage is claimed. A different console grammar is a visible
transport error. This option does not replace the configured released candidate.

This engine observes RCON and explicitly selected scratch-console command behavior only. It does not implement clients or
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

The campaign's positioned-anchor source fix was tested separately against vanilla,
unmodified upstream and the patched binary, with two repeats and the shared engine
lock. Both vanilla and the patch placed the marker at Y=64.25; upstream placed it
at Y=66.0275000333786. This targeted console validation is documented on
[`parity-lab-christine`](https://github.com/jkramer5103/Pumpkin/blob/parity-lab-christine/tools/parity-lab/docs/christine-positioned-anchor.md).

A reusable genuine-mismatch example is included in `lab/examples/`. With the
campaign's existing vanilla deployment and immutable current-upstream binary,
run from the lab root:

```sh
python3 -m lab shrink --targets runtime/targets.json \
  --scenario lab/examples/positioned-anchor.json \
  --reset lab/examples/positioned-anchor-reset.json \
  --versions lab/examples/positioned-anchor-versions.json \
  --pumpkin-console runtime/downloads/pumpkin-source-5b53f064af8708ba33fcaa533b81ca29a53a3310
```

The version file pins the campaign's official vanilla JAR and upstream binary
hashes. Other deployments must supply their actual version records and paths.
This is the known anchor regression fixed by `f123eb8`; it is not a new defect or
a synthetic server demonstration. The five steps preserve the source-existence
observation and the feet-position observation, with conditions evaluated through
scoreboard values. Only the tagged entities within the bounded arena and the
`pp_shrink` objective are changed.

Seeded fuzzing is finite and uses only generated, allowlisted commands:

```sh
python3 -m lab fuzz --targets runtime/targets.json --versions versions.json \
  --seed 1000 --seeds 10 --actions 12 --mode mixed --max-seconds 300
# For an upstream binary without RCON, add:
# --pumpkin-console /absolute/path/to/current-source-pumpkin
```

`--seed` begins a consecutive range of 1–20 unsigned 64-bit seeds. Each seed has
4–40 generated actions (default 12), replayed identically on both targets twice.
Modes are `scoreboard`, `blocks`, and `mixed` (alternating arithmetic and block
actions). The local RNG never changes Python's global random state. Generator v1
uses signed, bounded intermediates, positive add/remove operands, nonzero division
and modulo divisors, assignment, min/max, and swap. Integer floor division and
modulo form the model. No overflow behavior is claimed.

Block actions use inert stone/dirt/glass/gold blocks inside x/z 0..3 at y=80.
Single writes or rectangles touch at most four cells; reset fills touch at most
16. Every rectangle changes at least its first cell. Two distinct initial fills
establish air; cleanup removes generated blocks. Every block action checks all
16 cells, including those that should remain untouched. Block predicates record
success in a freshly zeroed score and positively assert that score: current
upstream supports redirected block conditions but rejects terminal block
conditions. Neither an empty condition response nor two equal failures can pass.
This tests block identities only, not properties, NBT, fluids or elapsed ticks.

The versions-file format is the same as shrinking. It is mandatory; local binary
hashes are saved and rechecked before each seed and reducer probe. Existing RCON
service identity remains declared provenance. Upstream console runs are explicitly
labelled `scratch-console`, and do not establish RCON support.

For block console comparisons only, the engine creates an original one-block
GameTest fixture and flat metadata in a new private world. A bounded loader probe
records commands and raw responses in `arena-bootstrap.json`; readiness requires
a successful actual block write. Networking remains loopback-only. The loader's
GameTest is expected to report a missing START block; it supplies chunk loading,
not a passing game test. Provisioning is separate evidence, never a parity pass.
Current upstream can unload this chunk despite `forceload` and tick freeze;
subsequent missing-chunk errors remain visible. Readiness does not guarantee
retention. No existing world/config or server service is replaced.

`--max-seconds` is one POSIX main-thread campaign deadline (0 < seconds <= 900),
covering lock waits, server operations and reduction. The one-shot deadline
interrupts active work, preserves an incomplete verdict and permits up to 30
seconds for bounded cleanup/shutdown. Operations time out within 5 seconds and
lock waits within 30 seconds. A swallowed engine/reducer timeout is checked again
before any new work. The CLI refuses to replace an existing process alarm. The
`--max-probes` budget (2–60, default 30) is shared across all reductions. There is
no infinite mode. Generation/config validation precedes the live deadline.

All seeds run before reduction. Completed engine runs with environment errors
are preserved and the finite campaign continues; an incomplete engine run stops
it. A campaign exits 2 if any infrastructure error occurred or the campaign was
interrupted/incomplete, 1 for other failures, and 0 only when every seed passed.
`complete=true` means the requested seed campaign finished, not that its results
passed: always check exit codes and individual reports.

Each `artifacts/fuzz/fuzz-SESSION/` contains its seed range, generator version,
limits, hashed target versions, exact `replay.txt`, per-seed scenario and generated
action JSON, run reports and raw transcripts, and a persisted failures array.
Only stable supported two-repeat mismatches with passing vanilla oracles are
sent to `lab.shrink.shrink_scenario`. Reduction preserves observation steps and
uses the existing real-target reruns, reset policy and exact failure identity;
unsupported, flaky and infrastructure outcomes cannot produce a minimized claim.
A probe/deadline exhaustion leaves reduction evidence without a minimality claim.
The saved reducer replay retains the scratch arena option. Replay entire
campaigns with their saved command and inspect pinned observations before
interpreting the limited deletion minimality.
