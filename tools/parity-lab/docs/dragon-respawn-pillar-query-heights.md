# Dragon pillar crystal query heights

Vanilla 26.3 `EndSpikeFeature.EndSpike` constructs its entity query using
`DimensionType.MIN_Y` and `MAX_Y`, the global coordinate limits -2032 and 2031.
These are distinct from the End dimension's Y0..256 block placement range.
Pumpkin previously used the latter for its pillar crystal query. During ritual
aborts, that narrower query left crystals outside that range permanently immune
and retained their ritual beams.

The bounded correction uses Pumpkin's existing equivalent global
limits, `generation::positions::MIN_HEIGHT` and `MAX_COLUMN_HEIGHT`. It does
not change pillar block generation or the dimension's build height.
`reset_spike_crystals`, `update_crystal_count`, and initial `spawn_crystals`
share this query; all receive the broader vertical range. The latter two
retain their existing center-based membership checks, a separate unconfirmed
lead. No chunk-generation algorithm or hot loop changes, so generation
benchmarks do not exercise this entity-query correction.

The focused Rust regression intersects actual end-crystal dimensions with the
pillar bounds, testing overlap and exact touch at global limits as well as
positions around Y0 and Y256. Live regression evidence uses an isolated End,
a headless official-protocol client, an actual fourth crystal item placement,
and naturally regenerated pillar crystals moved by commands. Explosion damage
before and after a participant is destroyed observes immunity/removal; tracked
metadata observes the beam. Five pairs of vertical positions include old build
height boundaries and the global upper boundary. The lower global boundary is
covered by the official implementation and Rust test because live entities
below the void have independent removal behavior.

The identical-probe comparison is complete. Vanilla and patched Pumpkin pass
all ten samples; baseline campaign 78 differs in five: Y=-4, -2, 256, 300 and 2030.999
retain immunity and beams after abort. All three targets agree at Y=-1.999 and
255.999 (reset) and Y2031, 2031.001 and 2032 (retain protection). Each target
completes five real item-triggered rituals with all client, player, cleanup,
shutdown, and beam/damage agreement controls passing. Source, binary, report,
probe, fixture, checker, official-source and protocol/log hashes are verified.
The new Rust regression fails on the baseline at Y=-2033.999 (overlap with the
lower global query edge). The patched regression and all 270 `pumpkin-world`
library tests (including generation parity tests), 493 `pumpkin-core` library
tests, workspace formatting, world/core all-target/all-feature Clippy, and the
debug server build pass. All Cargo checks ran under the shared lock with one
job, disabled debug info/incremental builds, and the specified 5 GiB/no-swap/
200% CPU scope. The existing `proc-macro-error2` future-compatibility notice
remains. Each target completed 1,355 controlled ticks. No errors or panics
were found in the server/client logs; normal debug/offline-mode, Java native
access and deprecated-Unsafe warnings remain.

The campaign 78 baseline binary has verified source and binary provenance.
Current upstream retains the Y0..256 query; no separate upstream-master binary
was reproduced. Local evidence is recorded in
`artifacts/christine-dragon79-{rust,live}-validation.json` and
`artifacts/christine-dragon79-source-provenance.json`; all three arena reports,
client packets, logs, fixtures and source/binary hashes are retained.

- Fixture: `fixtures/dragon-respawn-pillar-query-heights/cases.json`.
- Checker: `tests/check_dragon_respawn_pillar_query_heights.py REPORT TARGET`.
- Local evidence: `artifacts/christine-dragon79-*` in the deployment workspace.
- Official source: `EndSpikeFeature.EndSpike`, `DimensionType`,
  `EnderDragonFight.resetSpikeCrystals` and `updateCrystalCount`.
- Read-only upstream review: tracker, issue 3468, PRs 3661, 3407 and 3694.
  Multipart/contact/combat overlap remains deferred; no pillar-height fix found.

Headless state/protocol checks cannot establish rendered beams, full ritual
completion, persistence, Bedrock behavior or a whole boss fight. For a human
client check, move a regenerated crystal above Y256, abort the ritual, and
verify the beam ends and explosion damage can remove it; a crystal touching
the upper global query edge at Y2031 should retain its beam and immunity.
