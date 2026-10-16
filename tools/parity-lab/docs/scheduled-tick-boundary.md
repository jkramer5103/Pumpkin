# Scheduled block/fluid tick boundary

Current upstream `5b53f064af8708ba33fcaa533b81ca29a53a3310` executes positive
scheduled delays one tick late. A bounded source-console comparison against
vanilla 26.3 repeated twice verifies the initial water source and air below, air
through tick four, downward flow at tick five, and persistent flow at tick six.
Vanilla passes all four controls. Upstream fails only the tick-five observation.
Both transports verify exact game-time advancement; no sleep determines success.

Baseline: `artifacts/jaron-simulation-upstream/20261016T015605.489773Z-4cfb8915/`.
The run holds the engine shared file lock and uses the private one-chunk fixture
for current source, which has no RCON support. The permanent RCON release returns
unsupported-command and unloaded-world errors; those are separate retained data.

Vanilla 26.3 `LevelAccessor.createTick` uses current game time plus delay.
`ServerLevel.tick` advances time before block/fluid tick collection, and
`LevelTicks` collects trigger times <= current game time. Only these classes
were decompiled from the verified official server jar; no decompiled code is
published.

The patch advances the scheduler cursor before draining its bucket, treats zero
delay as due on the next step, and protects cursor/queue sampling with the same
mutex. Regression coverage includes delays 0/1/2/4/5/255, duplicate scheduling,
callback rescheduling, remaining-delay serialization and ring wrap. All three
new regressions fail on unpatched source; original log is retained as
`artifacts/jaron-simulation-scheduler-red.log`.

Overlap: open PR 4010 widens long-delay scheduling, but its inspected scheduler
and tests retain `delay + 1`. This independent boundary correction does not
integrate that PR or implement long delays. PR 3639 (inactive chunk gating) and
PR 3845 (forced chunks) address separate behavior. No upstream messages or PRs
were created.

Validation completed under the shared cargo lock, one build job, debug info and
incremental disabled, and a 5 GiB/zero-swap/200% CPU scope:

- `cargo fmt --all -- --check`: passed.
- `cargo test --locked -p pumpkin-world --lib`: all 267 tests passed, including
  the three regressions which failed before the patch.
- `cargo clippy --locked -p pumpkin-world --all-targets --all-features`: passed.
- `cargo build --locked -p pumpkin`: passed. Cargo emitted an existing dependency
  future-incompatibility notice for proc-macro-error2; no build failure.
- `python3 infra/validate_simulation.py --output artifacts/jaron-simulation-fixed
  --pumpkin-console runtime/downloads/pumpkin-jaron-scheduled-ticks-fixed` in a
  3 GiB/zero-swap/150% CPU scope: exit 0. Both vanilla and fixed passed all four
  observations twice (8/8 each). Both verified six simulated ticks per trial;
  initial one-tick capability probes also passed. No infrastructure errors or
  flakes, no console ERROR/panic lines; all three scratch processes stopped.

Final live evidence:
`artifacts/jaron-simulation-fixed/20261016T020838.197977Z-9354a9ae/`.
Build/test evidence: `artifacts/jaron-simulation-verify-build.json` and
`artifacts/jaron-simulation-verify-build-resume.log`. The interrupted earlier
scope remains preserved and is not counted as a passing suite.
Built binary SHA-256:
`cb10cb0da524952db4d141b7d8ed00538f01c2a8d3f815e09f03d3e1c0313b02`.
Final upstream/PR overlap recheck retained in
`artifacts/jaron-simulation-overlap-final.json`; upstream master is unchanged.

Long delays, chunk inactivity, sustained no-player chunk residency, random growth,
exact fluid properties, redstone networks and real-client visuals remain outside
this patch's live validation. Vanilla lamp shutoff and sand landing references
were observed separately; current-source counterparts remain blocked by property
syntax or chunk residency and were not promoted as passing checks.
