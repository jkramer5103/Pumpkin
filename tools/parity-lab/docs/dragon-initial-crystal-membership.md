# Initial fight scans preserve overlapping crystals

Pumpkin's initial fight scan can add a second crystal to an occupied pillar. Its
`spawn_crystals` membership check tested the crystal's position rather than its
hitbox. A crystal with its center half a block outside a pillar's query boundary
still overlaps that column, but the scan spawned another crystal on its cap.

The initial membership check now uses the existing world bounding-box query,
matching the count and reset queries. Existing centered and displaced crystals
remain in place. This changes only the initial scan's duplicate-prevention gate;
ritual generation, reset, counting and combat behavior retain their own paths.

Official Minecraft 26.3 `EnderDragonFight.scanState` does not create replacement
crystals. Vanilla creates them in `EndSpikeFeature.placeSpike`. Pumpkin's terrain
feature currently creates the pillar blocks only, so simply deleting its initial
crystal creation would remove fresh-fight crystals. That wider lifecycle mismatch
is separate and remains unresolved by this patch.

## Reproduction and validation

The isolated arena streams the End while frozen, verifies no dragon exists yet,
removes generated crystals and places six tagged crystals at Y120. Four overlap
the positive/negative X/Z pillar boundaries; two centered crystals are controls.
The first controlled fight ticks then run the initial scan. The probe checks
original crystal presence and positions, absence of extra crystals in each local
pillar box, a live headless observer, cleanup and stopped processes.

Initial official and campaign83 runs reproduce four extra Pumpkin crystals with
both centered controls passing. Official adds none in all six boxes. The fixture
is `fixtures/dragon-initial-crystal-membership/cases.json`; its offsets are relative
to the generated pillar radius because the reference world's pillar sizes vary.
The final fixture passes all six cases on official and patched Pumpkin; campaign83
passes the two centered controls and fails all four displaced overlaps with exactly
one extra crystal each. Original presence and positions, observer presence, dragon
tracking packets, cleanup and stopped-process checks pass. Baseline and patched
geometry and all 254 stimulus commands agree; scheduling-dependent readiness and
clock-poll commands are excluded from that command comparison. The same probe and
fixture hashes were used on all three targets. Server and client logs contain no
errors or panics. This is one final six-case trial per target; exploratory runs
are excluded from the counts.

All 495 `pumpkin-core` Rust library tests, workspace formatting, core Clippy with
all targets/features, and the debug server build pass under the shared Cargo lock
and resource limits. Existing `proc-macro-error2` future-compatibility warnings
remain. The retained live regression fails on the old membership gate and passes
on the correction. No duplicate unit test of the existing box-intersection helper
was added. Local evidence is recorded in
`artifacts/christine-dragon84-{before-validation,live-validation,rust-validation,source-provenance}.json`;
investigation scripts, binaries, logs, worlds and decompiled Java remain outside Git.

## Scope and upstream review

Fork master was already an ancestor of the Christine branch. Current upstream
retains the position-only initial membership gate. Read-only review on
2026-10-23 found no overlapping implementation in the open dragon PRs. PR3407
changes state reconciliation, bossbars and multipart behavior, not this gate;
PR3694 changes item placement and explosion damage. Those changes remain deferred.
The initially considered undead breath-healing lead exactly overlaps PR4107 and
was skipped without an implementation.

This is bounded server-state and headless protocol evidence. It does not prove
rendered-client behavior, Bedrock behavior, save/reload, natural crystal
generation, arbitrary pillar layouts, plugin cancellation or a whole boss fight.
The baseline is campaign83; no separate upstream-master binary is claimed.
