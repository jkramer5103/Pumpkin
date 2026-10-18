# Ender Dragon phase dispatch

A dragon restored in sitting-roar phase 7 switches to breathing phase 5 on active
tick 41. Vanilla immediately ticks the new phase, so its ten-tick breath warmup
ends on tick 50. Pumpkin caches the old handler until the next AI step, delaying
the cloud to tick 51.

`EnderDragon.aiStep` in the local Minecraft 26.3 server jar calls the new handler
once when the first handler changes phases, then uses that handler for steering.
The correction follows this bounded dispatch: no loop through subsequent phase
changes. It preserves existing NoAI, corpse, collision and part-update paths.

The opt-in `dragon-phase-redispatch.json` regression fixture repeats restored
roar-to-breath transitions and pauses NoAI at the boundary. It checks phase IDs,
actual area-effect-cloud presence and exact gametime deltas through ticks 49–51.
This is gameplay state evidence from isolated scratch worlds and a headless
protocol 777 player, not a rendered client capture.

## Validation

Vanilla and patched Pumpkin passed 46/46 focused checks; baseline 33d312c
passed 43/46, failing
the three tick 50 cloud-presence observations. All tick barriers, phase controls,
health controls and client-presence checks passed. The patch restores cloud
creation at tick 50 in all three transitions, including the NoAI pause.
Stimulus commands and fixture, source and binary hashes were verified. All three
scratch processes stopped; both Pumpkin logs confirm completed save and shutdown.
Vanilla logged saving but no final completion marker within the harness grace.
Server and client logs contain no panics, errors or exceptions.

460 pumpkin-core library tests, workspace formatting, pumpkin-core all-targets /
all-features Clippy and the debug server build passed under the shared build lock
and required resource limits. Existing proc-macro-error2 future-compatibility
warning remains.

Fork master 65bca3f is already an ancestor; current upstream 998c3f8 still has the
cached-handler dispatch. Open PR 3407 (a0cb2be) covers multipart damage/healing,
PR 3661 (e7e5449) covers part registration, and PR 3835 (3640e87) covers projectiles.
None adds same-step dragon phase dispatch.

## Limits and next work

These checks do not prove natural fight progression, arbitrary phase transitions,
flight steering parity or the complete sitting cycle. Cloud position, radius,
effects, lifetime and cleanup, scanning phase 6, and four-flame sequencing remain
independent leads. No upstream PR or issue is opened.

For real-client review, observe the transition from a restored roaring dragon
and record its first breath-cloud appearance beside a tick counter on vanilla
and Pumpkin. Capture: pending human recording.
