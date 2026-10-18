# Dragon sitting roar completion

Status: all 460 pumpkin-core library tests, workspace formatting, core clippy
with all targets/features, and the debug server build passed under the shared
Cargo lock and resource limits. Patched Pumpkin passed 58/58 focused gameplay
checks, matching vanilla.

Vanilla passed 58/58 checks; baseline passed 51/58. Six of eight fresh baseline
roars stayed in attacking phase after tick 41. The interrupted/reentered roar
changed to breathing before completing its new 40-tick wait. NoAI pause and
all tick/client controls passed. Identical stimulus commands and exact tick
deltas were verified; read-only clock polling counts differ between servers.

Mojang 26.3 `DragonSittingAttackingPhase.begin` resets `attackingTicks`, and
`doServerTick` uses `attackingTicks++ >= ROAR_DURATION` (40) to switch to sitting
flaming. The dragon therefore remains roaring for 40 active ticks and always
starts breathing on tick 41. Baseline Pumpkin instead randomly chose whether to
breathe at this boundary, could take off based on total sitting time, and retained
its roar clock when the phase was interrupted and reentered.

The bounded correction resets the roar clock on phase entry and always
transitions to breathing at the vanilla boundary. The existing damage-triggered
takeoff gate is outside this task and overlaps upstream PR3407; it is preserved.
The breathing timer reset is retained because Pumpkin's breathing phase does not
yet perform that reset in its own `begin` method.

Upstream master 998c3f8 still has the incorrect roar logic. Open PR3407 at a0cb2be
changes the independent damage gate in the same file, without fixing roar
completion or reentry. PR3661 at e7e5449 concerns hitbox lookup. Fork master
65bca3f is already an ancestor of this campaign branch. No existing implementation
of this correction was found in the open dragon PR search.

The permanent `dragon-sitting-roar.json` fixture checks eight fresh roars at
40/41 ticks, interrupted/reentered roars, and a NoAI pause. It uses frozen ticks,
a headless protocol 777 client and a bounded scratch arena. It does not prove
breath cloud timing, damage, the complete sitting cycle, natural End fights,
phase metadata rendering, or rendered-client visuals. Scanning phase 6 remains
unimplemented. No full fight parity claim is made.

The fixed replay used the unchanged permanent fixture and stimulus commands;
source/binary/fixture hashes matched the recorded build and references. All three
scratch server processes stopped, and both Pumpkin shutdown completion markers
were verified. Vanilla logged saving and RCON shutdown without a complete shutdown
marker within the harness grace. Server and headless-client logs had no errors or
panics. Existing Java native/Unsafe and Rust proc-macro-error2 future-compatibility
warnings remain. One unused historical binary from this lane was losslessly
archived with decompressed hash verification to preserve build disk headroom.

For a real-client check, observe a sitting roar through its transition to breath,
then interrupt/reenter the roar and verify it starts a fresh countdown. Capture a
recording of the phase transition and breath animation. No such visual capture
was produced by this task.
