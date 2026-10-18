# Wither bossbar audience

Pumpkin selected an active Wither's bossbar audience using a fixed 50-block
three-dimensional sphere. Vanilla WitherBoss.startSeenByPlayer and
stopSeenByPlayer use the entity tracker instead. Its ChunkMap.TrackedEntity
uses horizontal distance, the observer's view distance and chunk visibility.
A player above the boss can therefore see its bar beyond 50 blocks; a player
within 50 blocks must lose the bar when outside the entity tracking range.

The correction uses the Wither's existing TrackedEntity.seen_by audience when
reconciling bossbar players. It preserves the existing progress, title, flags,
AI scheduling and death cleanup. Shared tracking code is unchanged.

Regression: `lab/examples/wither-bossbar-tracking.json`, two trials with one
charging Wither in a small arena and a connected protocol-777 client. Move the
observer near,
vertically above 50 blocks, horizontally beyond the configured 32-block tracking
range while still inside 50 blocks, then back. Correlate the bar UUID's ADD and
REMOVE packets with actual Wither tracking, and check observer/boss positions,
full health and cleanup. Boss position assertions cover its bounding box in the
arena; they do not prove identical flight or collision physics.

Results: vanilla and patched Pumpkin each passed 56/56 checks; baseline passed
52/56, failing only the two audience cases in each trial. All three targets used
the identical fixture and command traces. Actual Wither spawn, removal and
re-entry packets were verified, including the same bossbar UUID on return. The
client acknowledged chunk batches and player loading; earlier probes without
these acknowledgements had no Wither spawn packets and are excluded.

All 444 existing core library tests, workspace formatting, core
all-targets/all-features Clippy and the debug server build passed under the shared
Cargo lock and resource limits. All three scratch processes stopped and cleanup
passed; both Pumpkin save/stop completion markers were verified. Final server
and client logs contain no errors or panics. Vanilla full-save completion is
unverified. Runtime evidence is retained outside the repository in
`artifacts/jaron-wither40-{validation,verify,final-logs,source-provenance}.json`.
The built executable SHA-256 is
`92843052d409dc61d07bae8fea2607eb7cddca2e2de6f2d67c8ae7b044178fa5`.

Scope: this fixes audience selection during existing active-AI updates. Vanilla
pairs/unpairs bars synchronously with entity tracking; Pumpkin still reconciles
on its AI tick. NoAI membership/timing and immediate frozen-tick updates are not
fixed or claimed. Open upstream PR4092 already changes NoAI bossbar dispatch but
retains the same 50-block audience filter, so this does not duplicate that fix.
No rendered bossbar, Bedrock, multiplayer or whole-fight proof is claimed. A real
Java client can check the bar while flying above the boss, leaving its render
range and returning.
