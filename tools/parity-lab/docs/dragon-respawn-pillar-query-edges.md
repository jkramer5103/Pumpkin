# Dragon pillar crystal query edges

Vanilla 26.3 `EndSpikeFeature.EndSpike` sets the positive horizontal edges of
`getTopBoundingBox()` to `centerX + radius` and `centerZ + radius`. Pumpkin adds
one block to both. During respawn aborts, that extra strip resets crystals whose
hitboxes only touch or lie outside the vanilla pillar query: their permanent
immunity and ritual beam disappear, and explosion damage can remove them.

The bounded correction removes the extra block on both positive edges. The
height range is unchanged. Other callers are `update_crystal_count` and initial
`spawn_crystals`; they receive the corrected horizontal range but retain their
existing center-based membership checks. Their hitbox semantics are separate,
unconfirmed gameplay leads. The pillar generation loop and its inclusive block
coordinates do not use this query, so chunk generation and its performance are
unchanged; generation benchmarks do not exercise this correction.

A Rust regression intersects actual end-crystal dimensions with the spike query
at overlapping, exactly touching and outside positions on both positive edges.
The test failed before the fix at the positive X touch boundary (crystal at
46, -24.5 for center 42,-25 and radius 3). Initial import-error runs are excluded.
The Rust patch passes 269 `pumpkin-world` library tests
(including stage parity), 493 `pumpkin-core` library tests, workspace formatting,
world/core all-target/all-feature Clippy and the debug server build. All Cargo
operations used the shared lock, one job, disabled debug info/incremental builds,
and the specified 5 GiB/no-swap/200% CPU scope. An existing `proc-macro-error2`
future-compatibility notice remains.

The first baseline arena failed before initial dragon spawn while the compiler
was active; it is excluded. The first fixed attempt was stopped while waiting
for the engine lock. All 3 final targets used one identical probe with a longer bounded setup wait.
Vanilla and patched Pumpkin match all 12 sampled crystals. Campaign 77 differs
in 6 samples: offsets 1, 1.001 and 1.999 on both positive edges incorrectly lose
immunity and beam metadata. The overlap controls (0.5 and 0.999) reset on all
targets; offset 2 retains immunity on all targets. Each target completed 6 actual
item-triggered rituals and 1,566 controlled ticks. Before-abort immunity,
after-abort damage/removal, beam packets, player/client, cleanup and shutdown
checks pass. Source, binary, probe, fixture, checker, reports, logs and packet
hashes were verified. No errors or panics were found; normal debug/offline-mode
and Java native-access warnings remain.

Local evidence: `artifacts/christine-dragon78-{rust,live}-validation.json`,
`artifacts/christine-dragon78-source-provenance.json` and the three final
`christine-dragon78-arena-*/report.json` files. The baseline binary is the
previously validated campaign 77 build. Current upstream retains the extra
positive-edge block; no separate upstream-master binary was reproduced.

The isolated comparison uses the existing arena tooling and a headless official
protocol client. Each target starts a fresh End fight, kills its dragon, places
the fourth ritual crystal using an actual item-use packet, and advances 185 ticks
to regenerate two pillar crystals. Commands move those crystals to six offsets
on the positive X/Z edges at Y120. Explosion damage before/after destroying a
ritual participant checks immunity, entity removal, and tracked beam metadata.

- Fixture: `fixtures/dragon-respawn-pillar-query-edges/cases.json`.
- Checker: `tests/check_dragon_respawn_pillar_query_edges.py REPORT TARGET`.
- Official implementation: `EndSpikeFeature.EndSpike`,
  `EnderDragonFight.resetSpikeCrystals` and `updateCrystalCount`.
- Read-only upstream review: tracker and issue 3468; PRs 3661, 3407, 3694 cover
  different multipart/combat work. No open spike/pillar query fix was found.

Headless server-state/protocol evidence cannot prove rendered beams, successful
full ritual completion, persistence, Bedrock behavior or a whole boss fight.
For a human client check, move a regenerated crystal just outside a pillar's
positive query edge while its hitbox touches the edge, abort the ritual, and
verify its beam and immunity remain; an overlapping crystal should lose both.
