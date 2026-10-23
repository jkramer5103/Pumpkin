# Wither bossbars after changing dimensions

A player who leaves a tracked Wither's dimension must lose its bossbar. Pumpkin
removed the viewer from entity tracking but left bossbar removal to a later
Wither tick. The departed player was no longer in that world's player list, and
the boss could stop ticking when its chunk became inactive. The client retained
the old bar.

Entity tracking now calls a default no-op `Mob.stop_seen_by_player` when removing
a pairing, broadcasting entity removal, or forgetting a respawned viewer. Wither
implements the callback by removing an existing audience entry and sending that
player the bossbar removal packet directly. This happens independently of AI,
chunk activity and world-list membership. Existing audience selection, progress
updates and other mobs retain their current behavior. No other boss implements
the new hook.

Vanilla 26.3 reference: `ChunkMap.TrackedEntity.removePlayer` calls
`ServerEntity.removePairing`, which invokes `WitherBoss.stopSeenByPlayer`;
`ServerBossEvent.removePlayer` sends the removal packet to that player directly.
Pumpkin's `World.remove_player` removes the player from its world list before
calling the entity tracker, which still has the actual departing player.

The [fixture](../fixtures/wither-dimension-bossbar/cases.json) and
[packet checker](../tests/check_wither_dimension_bossbar.py) cover two trials of
an active Wither, a charging Wither, and a same-dimension distance control.
They require an initially tracked Wither and visible bar, verified destination
player dimension, one removal packet for the original bar UUID, cleared observer
bossbar state, unchanged boss health and preserved spawn phase after return, client liveness,
cleanup and controlled simulation ticks. Boss state is queried explicitly in the
Overworld. All gameplay commands are identical between targets; only transport
and game-time polling differ.

Final Rust validation passed: 450 `pumpkin-core` library tests, workspace
formatting, core all-target/all-feature Clippy and a debug server build. All Cargo
operations used the shared lock, one build job, disabled debug information and
incremental compilation, and the required 5 GiB / zero-swap / two-CPU scope.
The existing `proc-macro-error2` future-compatibility notice remains.

The identical final protocol replay passes all 94 focused checks on vanilla 26.3.
Campaign85 passes 86/94, failing exactly eight removal-packet and stale-observer
assertions across the four dimension departures. Both distance controls pass.
Patched Pumpkin passes 94/94, matching vanilla. Every target runs the same six
cases and 320 controlled simulation ticks. The finalizer verified identical
probe/fixture/gameplay-command hashes, source hashes matching the compiled
binary, original bar UUID removal, destination dimension, restored boss health
and phase, cleanup and stopped processes. Successful logs contain no errors or
panics. Evidence is retained outside Git in
`artifacts/jaron-wither86-live-validation.json`,
`artifacts/jaron-wither86-rust-validation.json` and
`artifacts/jaron-wither86-source-provenance.json`.

Overlap: fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is
already an ancestor of this branch. Upstream
`9c04f714bb7eb26579c652f9744895d465ee902b` still polls Wither audience membership
and lacks the removal callback. Reviewed all 324 open PRs and relevant file
patches including 3432, 3708, 3793 and 3865; none adds this callback. The initial
NoAI audience lead is already corrected by upstream's AI foundation change and
was skipped. Its implementation was not copied into this bounded fix.

Limits: headless Java protocol/server-state evidence, no rendered client,
Bedrock or whole boss fight. Return-to-world commands restore the fixture between
cases; vanilla re-pairing was not observed within the short return window, so
re-entry is not a parity assertion. Exact inactive-world countdown timing remains
separate: Pumpkin pauses this boss without an active chunk despite the fixture's
forceload request. Boss state was not selectable during the dimension absence,
so health and spawn-phase assertions are made after return. Timer controls assert the phase and bounded timer range rather
than identical cadence. Initial NoAI audience scheduling, simultaneous
reconnects, mob-specific respawn behavior and plugin interactions are unverified.

Superseded attempts are excluded from final evidence: the first scratch config
had the Nether disabled; another queried the boss without an explicit dimension
and assumed inactive-world ticking. A source attempt that only searched all
worlds passed Rust checks but failed the actual packet comparison because the
boss stopped ticking. The final callback replaces that attempt.

For a rendered check, stand near an active and then a charging Wither in an
isolated arena, change dimensions, and confirm its bar disappears. Also walk
beyond tracking range in the original dimension and confirm the same result.
Capture the bar before each departure and its disappearance afterward. No
rendered-client capture has been made.
