# Wither spawn completion sound dispatch

The Wither used a chunk-tracked, local level event when its spawn invulnerability
expired. Vanilla 26.3 uses global level event 1023, unless the boss is silent.
Clients received a local volume flag and the boss location rather than vanilla's
global sound at an observer-relative location. Chunk tracking could also omit
distant recipients.

The Wither now uses `World::sync_global_world_event`. That helper follows vanilla
`ServerLevel.globalLevelEvent`: with `global_sound_events` enabled, send to every
world's Java players, positioning the sound at the boss block for nearby players,
32 blocks toward it for distant same-world players, or at the observer for players
in another world. With the rule disabled, send an ordinary local event within a
strict 64-block radius in the source world. The existing in-memory silent flag
gate is retained. NoAI bosses, unfinished charges and already-active bosses do
not emit the spawn event.

The helper also serves End portal activation. Its event obeys the same vanilla
contract; ordinary sound packets and other local world events are unchanged.
There is no existing plugin sound event on either helper path to preserve.

## Regression and validation

`wither-spawn-sound.json` contains one bounded isolated arena fixture with near,
distant, charging, NoAI, active and local-rule controls. Protocol 777 packet
capture is required in addition to its command observations. The near and distant
positions are `(15,84,15)` and `(-24,84,-24)`, with the boss at `(24,80,24)`.
Expected global packets locate the sound at `(24,80,24)` and `(-2,82,-2)`.
A Rust regression covers near, distant, 32-block boundary and other-world placement,
including negative-coordinate flooring.

All 444 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared build lock and resource
limits. In two isolated trials, vanilla and patched Pumpkin each passed 126/126
checks; the baseline passed 118/126. Its eight failures were two wrong global
flags nearby, two wrong global flags and two wrong event positions at a distance,
and two local events delivered beyond 64 blocks with the global rule disabled.
All charging, NoAI, active-boss, near-local, health, observer and cleanup controls
passed. The fixture verifies exact decimal player positions and allows two
tracking-settling ticks before spawning each boss. Fixture and gameplay-command
hashes match across all targets, and source/binary hashes match the Rust build.
All three scratch processes stopped; neither server nor client logs contained
errors or panics. Pumpkin saves completed; vanilla full-save completion was not
verified within the harness shutdown grace. Actual evidence is in the live lab's
`artifacts/jaron-wither39-*` records. Open Wither PRs and sound PR3739 were checked;
PR3739 concerns ordinary sound packet radius filtering, not global level events.
Fork master was fetched and is already an ancestor of this campaign branch.

An attempted `Silent:1b` control exposed a separate general entity NBT gap:
Pumpkin does not read that key, so the fixture could not construct a silent boss.
That case is excluded and is not counted as a pass. No Silent-NBT source change
is included; only the original in-memory gate is verified by source inspection.

## Client follow-up

No rendered audio, full boss fight, Bedrock, cross-dimension live playback or End
portal activation proof is claimed. In a disposable world, stand near a completing
Wither and then outside its tracking range: hear the spawn sound in both cases.
Disable `global_sound_events` and confirm sound stays local. The existing Silent
NBT setup gap needs a separate correction before it can serve as a playback
control. A second player in another dimension should hear the global event at
their own position. Capture a real-client recording with sound
before any human upstream submission; none is being opened by this campaign.
