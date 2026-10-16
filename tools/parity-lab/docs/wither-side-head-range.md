# Wither side-head acquisition range

Pumpkin's side heads could acquire a visible iron golem at offset `(18, 0, 18)`,
about 25.46 blocks away. Vanilla 26.3 rejects that candidate: its box search is
followed by a spherical 20-block combat target predicate. Pumpkin searched the
same box but omitted that predicate, then fired using the separate 30-block
retention limit.

The Wither now uses the existing `TargetPredicate::create_attackable()` with a
20-block maximum distance when acquiring side-head targets. The Wither-friends
tag exclusion remains explicit. Self, living/alive, and line-of-sight checks
move into the existing predicate, which also applies combat eligibility and
alliance checks. No shared entity or combat files change. Existing targets keep
their separate 30-block retention limit.

Reference implementation inspected: vanilla 26.3 `WitherBoss.TARGETING_CONDITIONS`
and `customServerAiStep`, then `ServerEntityGetter.getNearbyEntities` and
`TargetingConditions.test`. The inspected decompiled classes stay outside Git.
The [mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468)
provided leads; the missing spawn-window goal is a separate candidate. The
upstream overlap check found no matching acquisition fix. Open PR 3865 concerns
Wither death/drop behavior; PR 3793 only changes the Wither tick-count field.
Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already in this branch;
upstream master remained `5b53f064af8708ba33fcaa533b81ca29a53a3310` at recheck.

Three focused regression fixtures cover outside range `(18, 0, 18)`, inside
range `(14, 0, 14)`, and the exact 20-block boundary `(12, 0, 16)`. Each uses a
fresh isolated arena, Easy difficulty to disable idle dangerous skulls, a
stationary golem, one disabled-AI registration tick, and 40 verified sampling
ticks. Every sampling tick teleports the Wither to its origin and clears its
velocity so vanilla pursuit cannot move it into range. Skull entities are sampled
and removed each tick. Position, golem presence, and clear-path controls must
pass. A creative offline protocol-777 client holds Pumpkin chunks loaded;
vanilla uses forceload. The task-local runner waits for the far arena corner
before setup. Repeat every case twice.

The pre-fix binary from `af7958ec707b77cee47dd6bd3b9b8a9bbe53a40a` fires outside
range in both clean repetitions. Its inside and boundary controls pass. Vanilla
passes all six range observations and all position/path/environment controls.
The first exploratory baseline outside case had an unloaded-chunk setup error;
it is retained but excluded. Clean baseline and reference evidence are retained
outside Git at `artifacts/jaron-wither-range-fixtures-20261016T115941.345022Z/`
and `artifacts/jaron-wither-range-fixtures-20261016T115841.833023Z/`.

Rust validation passed under the shared build lock, one Cargo job, disabled debug
info/incremental compilation, and the required 5 GiB/no-swap/two-CPU caps:
`cargo fmt --all -- --check`, all 443 `pumpkin-core --lib` tests,
`cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
`cargo build --locked -p pumpkin`. Only the existing dependency
`proc-macro-error2` future-incompatibility notice appeared. These tests do not
replace the runtime regression fixtures.

Patched Pumpkin also passes all six range observations, 18 position/path
controls, and six environment guards across both repetitions, matching vanilla.
Its report is retained at
`artifacts/jaron-wither-range-fixtures-20261016T121139.881581Z/report.json`.
The source and fixture SHA-256 values match the validated snapshots; the patched
binary SHA-256 is
`99c3fdfe6732a268c0e76d406025ae094901460c410768714fdd35789b4aab0c`.
The raw transcripts show 41 verified ticks per case. All 18 scratch arenas
stopped, and their console logs contain no ERROR or panic lines. Final assertions
and Rust check results are retained at `artifacts/jaron-wither-range-completion.json`
and `artifacts/jaron-wither-range-verify.json`. An earlier replay was stopped
while waiting for the shared arena lock, before it ran any cases; its empty
incomplete report is excluded.

The shared target predicate still lacks vanilla's sneaking/invisibility range
scaling. Acquisition eligibility beyond ordinary golems, already acquired target
eligibility changes, attack timing/trajectory/damage, and a complete boss fight
are outside this validation. No human visual capture was made. A human check can
hold a Wither stationary in an isolated arena and move a visible golem across
the diagonal 20-block acquisition boundary, then inspect head aim and skulls in
a real client; move existing targets beyond 30 blocks before repeating so their
retention does not obscure acquisition.
