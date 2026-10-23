# Restrict the first dragon XP reward to the fight boss

Before the first End fight was completed, Pumpkin awarded 12,000 XP to every
dragon dying in that world. An unrelated summoned dragon should award 500 XP.
Vanilla 26.3 `EnderDragon.aiStep` attaches a world fight only when the dragon's
UUID equals its tracked UUID; `tickDeath` selects the first-kill reward only for
a dragon attached to a never-completed fight. Pumpkin looked only at the
world fight's completion flag.

`DyingPhase::death_experience` now requires the tracked UUID as well as an
unfinished first fight. The periodic and final death-animation payouts use the
same corrected reward. The tracked first boss retains 12,000 XP; unrelated,
repeat and non-fight dragons receive 500 XP. Existing mob-drops gating remains
in both payout paths. Only the boss-specific dying-phase Rust file changes.
The focused Rust regression covers an unrelated UUID, the tracked first boss,
a previously completed fight, no tracked dragon and no world fight.

Fresh isolated official 26.3 and campaign88 baseline arenas each run four trials
with a connected creative Java protocol777 client. The actual player collects
the orbs after 200 controlled ticks, and level/point queries measure total XP.
Vanilla yields 500, 0, 12,000 and 500 XP respectively for an unrelated dragon
before the first kill, an unrelated dragon with mob-drops disabled, the tracked
first boss, and an unrelated dragon after the first kill. The unchanged
baseline yields 12,000, 0, 12,000 and 500 XP. All 44 death stimulus commands match.
Both targets boot, retain the player/client, collect all orbs, clean up and stop.
Their server/client logs contain no error or panic lines. Runtime artifacts
retain report, log, probe, client, binary and official-jar hashes.

All 496 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock with one
build job, disabled debug info/incremental and the prescribed memory/CPU limits.
Removing the UUID condition makes the focused regression fail with 12,000
instead of 500 XP. The existing `proc-macro-error2` future-compatibility warning
remains. The final patched binary matches all four vanilla XP totals:
500, 0, 12,000 and 500. All 44 death stimulus commands and their 200 requested
ticks per trial match across the three targets. Player/client presence, no XP
before tick155, both payout observations under the drops rule, complete orb
collection, cleanup, shutdown and clean error/panic logs pass. Runtime artifacts
link the immutable binary back to the tested Rust source hashes.

Fork master was fetched and is already an ancestor. Fetched upstream master
1feb9d85 retains the same world-only XP calculation. All open PR pages and the
file diffs of PR3407, PR3661 and PR4105 were inspected. The multipart design
changes remain deferred; PR4105 concerns loot gating and explicitly leaves
specialized dragon XP work separate. None changes reward selection. The file
was reserved before edits, and the other lane's pathfinder file is untouched.

Evidence is headless server state and real player XP pickup, with one arena per
target. Health is set to zero by command to isolate the reward path; combat,
rendered animation, full fights, save/reload, plugins and Bedrock are untested.
Raw tag-selector corpse queries exclude dead living entities and are excluded
from lifecycle proof. Setup and XP-collection tick counts vary; the death
stimuli and their requested 200 ticks match. Vanilla uses client72 and Pumpkin
uses client86 for stationary postteleport chunk streaming. Clients terminate
after observations without final client JSON. No standalone upstream-master
binary is built.

For a human check in a disposable End before killing its natural boss, summon
an extra dragon, kill it through combat, and collect its XP. It should award
500 XP. The natural first boss should still award 12,000 XP. A rendered-client
recording of both rewards remains a manual check.
