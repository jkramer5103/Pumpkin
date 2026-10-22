# Wither skull dangerous-state reload

Changing an existing skull's `dangerous` flag left nearby Java clients with stale
metadata controlling its black/blue variant. Removing the flag also retained the
old server value instead of resetting it to false. The skull NBT reader now calls the
existing `set_dangerous` method with vanilla's false default, keeping gameplay
state and observer metadata together.

Official 26.3 `WitherSkull.readAdditionalSaveData` calls
`setDangerous(input.getBooleanOr("dangerous", false))`. Its setter updates synced
entity data. Pumpkin's data entity accessor calls `read_nbt_non_mut`, which reaches
`read_custom_nbt`; it does not reinitialize the tracker after a live reload.
Initial spawning does initialize the tracker, explaining why newly summoned
blue skulls were already correct.

The focused fixture is `fixtures/wither-skull-dangerous-sync/cases.json`. An
existing headless protocol-777 observer records spawn and metadata packets in an
isolated, frozen arena. Two trials cover black-to-blue, blue-to-black, removing
the flag, preserving it through an unrelated merge, and unchanged true/false
controls. Both targets use identical commands and 61 controlled ticks. The
checker reads server NBT and metadata field 8, reconstructing the observer's
cached flag from the spawn default and subsequent updates. Position, zero
velocity, creative-player presence, client survival, cleanup and server shutdown
are checked as controls.

Before the patch, official vanilla passed 144/144 checks and campaign commit
`6abbe935ea92206d8ad99f189fe34b34725a8430` passed 130/144. The 14 failures were
exactly six missing metadata deltas, six stale observer flags, and two missing
server resets. The checker fails on the unpatched baseline without its explicit
baseline expectation mode.

The patched binary passed 144/144 checks with identical commands and controlled
ticks. Source and copied-binary hashes were verified, and all six server/client
logs were checked for errors, panics and fatal exceptions. Workspace formatting,
450 `pumpkin-core` library tests, core Clippy with all targets and features, and
the debug server build passed under the shared Cargo lock with one build job,
debug information and incremental compilation disabled, and the required memory
and CPU limits. The existing `proc-macro-error2` future-compatibility notice remains.

Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor of
the campaign branch. Refreshed upstream master
`9c04f714bb7eb26579c652f9744895d465ee902b` retains the same NBT reader. All 322
open pull requests were inspected for leads; relevant PRs 3835 (flight/collision
and hit effects), 4107 (target selection), and merged 4092 (AI foundation) do not
change this reader. No upstream master binary was separately built.

This is server-state and headless packet evidence. It does not prove rendered
color changes, Bedrock behavior, disk unload/reload behavior, naturally fired
skulls, projectile flight or whole-fight parity. No new Rust setter test was
added: the regression needs a real world, tracker and observer connection.

For a rendered play test, summon a stationary skull with
`summon minecraft:wither_skull ~ ~2 ~ {Tags:["pp_skull"],Motion:[0d,0d,0d],NoGravity:1b}`.
Set its flag using `data merge entity @e[tag=pp_skull,limit=1] {dangerous:1b}` and
expect blue; set it to `0b` and expect black. Set it to `1b` again, then run
`data remove entity @e[tag=pp_skull,limit=1] dangerous` and expect black.
Capture: a real-client recording showing all three transitions is still needed.
