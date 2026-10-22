# Wither spawn immunity after an NBT reload

Removing `Invul` from an existing Wither left its spawn immunity active. Vanilla
resets the timer to zero, so ordinary damage starts working immediately. The Rust
reader now always calls the existing synchronized timer setter with zero as the
missing-field default. Present timer values continue to be read unchanged.

Official 26.3 `WitherBoss.readAdditionalSaveData` calls
`setInvulnerableTicks(input.getIntOr("Invul", 0))`. Its damage handler rejects
ordinary damage while that timer is positive. Pumpkin's entity data accessor
reloads the NBT through `read_nbt_non_mut`, the mob blanket implementation and
`mob_read_nbt`. The existing timer setter updates both the atomic gameplay value
and tracked metadata field 19; using it also clears observers' cached spawn timer.

The regression fixture is `fixtures/wither-invul-reload/cases.json`, checked by
`tests/check_wither_invul_reload.py`. An existing protocol-777 headless observer
joins an isolated frozen arena. Two trials cover removing a positive timer,
explicitly setting zero, preserving a positive timer through an unrelated merge,
replacing it with another positive timer, and removing an already zero timer.
The boss has NoAI and NoGravity to isolate the reload from natural countdown and
movement. Each case tests ordinary damage before and after the operation, health,
server timer, observer metadata and cached timer, with position, player/client,
cleanup and stopped-process controls. All three targets execute identical commands
and 526 controlled ticks. The checker must fail on the unpatched baseline unless
its explicit baseline-expectation mode is supplied.

Workspace formatting, 450 `pumpkin-core` library tests, core Clippy with all
targets and features, and the debug server build passed under the shared Cargo
lock with one build job, debug information and incremental compilation disabled,
and the required memory and CPU limits. The existing `proc-macro-error2`
future-compatibility notice remains. The initial disk-space guard stopped before
Cargo ran; only this lane's obsolete binary caches were compressed before retry.

Official vanilla passed 180/180 focused checks; the campaign78 baseline passed
170/180. The ten failures were exactly two trials of five assertions after
removing a positive timer: server timer, metadata delta, cached observer timer,
damage acceptance and resulting health. Initial exploratory reports with
insufficient corpse cleanup are excluded. The final probe waits 25 ticks, clears
drops and verifies an empty arena before each summon. The patched binary passed
180/180 with identical commands and controlled ticks. Source, copied-binary,
fixture, checker, probe and report hashes were verified; all six server/client
logs were checked for errors, panics and fatal exceptions. This verifies both
ordinary damage acceptance and the observer timer reset after the reload.

The source baseline is campaign78, `4b8bfb1bf7880ab9cd5fb34d896e9a243c390b0d`.
Refreshed fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an
ancestor of the branch. Upstream master `9c04f714bb7eb26579c652f9744895d465ee902b`
retains the same reader defect. All 323 current open pull requests were inspected; PR3865
(death drops) and PR3835 (projectiles) do not change this reader. Tracking issue
3468's invulnerability-window goal is already implemented by an earlier campaign
patch, so it was not selected again.

This covers live NBT reload, ordinary damage and observer packets. It does not
prove disk unload/reload, malformed NBT, natural construction/countdown, Bedrock,
rendered appearance or whole-fight parity. A separate upstream-master binary was
not built. A Rust getter/setter test would not exercise the real reload, tracker
and damage path; the focused regression uses the actual running server.

For a human play test in a disposable arena, summon a Wither with
`summon minecraft:wither ~ ~2 ~ {Tags:["pp_boss"],NoAI:1b,NoGravity:1b,Invul:200}`.
Run `damage @e[tag=pp_boss,limit=1] 7 minecraft:generic` and expect rejection. Run
`data remove entity @e[tag=pp_boss,limit=1] Invul`, then repeat the damage command
and expect success with health 293. With a real client, check the spawn appearance
also resets. Capture: a real-client recording is still needed before any human PR.
