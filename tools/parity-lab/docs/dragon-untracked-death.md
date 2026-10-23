# Ignore deaths of unrelated Ender Dragons

After the tracked Ender Dragon was killed, Pumpkin cleared its tracked UUID.
`DragonFight::set_dragon_killed` then accepted any dragon's UUID because its
rejection condition only applied when a UUID was present. Killing an extra
summoned dragon could activate the exit portal again and award another gateway.

Vanilla 26.3 `EnderDragonFight.setDragonKilled` requires the killed dragon's UUID
to equal the tracked UUID. `EnderDragon.aiStep` also only attaches the matching
dragon to the fight. Pumpkin's completion callback now requires that same exact
match, including when no dragon is tracked. Both the command-kill callback and
normal death animation call this method; the tracked boss keeps its existing
completion path. The change does not alter other callbacks or dragon tracking.

An isolated fresh End arena with a connected creative protocol client first
kills an unrelated dragon while the tracked boss lives, then kills the tracked
boss, then kills two more unrelated dragons. Each trial places a diamond block
in the exit portal before the death. Only the tracked boss should regenerate
the portal and replace the block. Both extra deaths after completion incorrectly
replace it on the immutable campaign87 baseline. Vanilla preserves it. The
unrelated-death-while-alive control and tracked-boss-death control pass on both.
The committed fixture and focused checker exercise actual server block changes
and entity removal, and the checker rejects the old binary.

Workspace formatting, all 495 core Rust library tests, core Clippy with all
features/targets and the debug server build passed under the shared Cargo lock,
one build job, disabled debug info/incremental and the prescribed memory/CPU
limits. The existing `proc-macro-error2` future-compatibility warning remains.
The patched binary and vanilla pass all four focused trials. The old binary
fails both postfight unrelated deaths and the final preservation observation.
All 35 trial commands match across targets after normalizing podium height.
All three servers boot, retain the connected player/client, remove the tested
dragons, clean up and stop; successful server/client logs contain no error or
panic lines. Source, immutable binaries, official jar, probe, clients, fixture,
checker, report and packet/log hashes are recorded in the runtime artifacts.
The regression exercises a real world rather than duplicating the UUID check
in a new Rust unit test.

Fork master was fetched and is already an ancestor. Read-only upstream master
1feb9d85 retains the exact UUID guard. Fresh open dragon PR searches and the
full file diffs of PR3407 and PR3661 were inspected; neither corrects this guard.
PR3407 changes nearby completion bossbar handling but keeps the guard. This
boss-specific file was reserved before editing; the other lane's shared
living/mob files are untouched.

The evidence is one headless Java protocol777 arena per target, with no rendered
client or whole-fight claim. Command kills exercise real removal and completion
callbacks; combat damage and the 200-tick corpse path are not runtime-tested by
this task. Gateway placement, egg placement, save/reload, ritual respawn,
Bedrock and plugin behavior are not separately asserted. Portal height is
resolved from each world's podium because terrain generation differs. Vanilla
uses the existing client72 and Pumpkin uses client86 with its stationary
post-teleport position packet needed for chunk streaming. Setup tick counts can
differ, while the trial commands match after normalizing portal height. Clients
terminate after observation without final client JSON; live player presence and
received spawn packets remain in the evidence.

For a human check in a disposable End, kill the fight dragon, alter one exit
portal block, then summon and kill another dragon. The altered block should
remain. A fresh ritual-spawned boss should still activate the portal on death.
No rendered-client proof is claimed.
