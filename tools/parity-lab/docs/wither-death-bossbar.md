# Wither bossbar during the death animation

Pumpkin removed a Wither's bossbar on the first tick after lethal damage, while
its corpse remained tracked for the 20-tick death animation. Vanilla retains the
bar and its last progress until corpse removal. This also applies when a Wither
is killed during charging or after NoAI is enabled on an already tracked boss.

The Rust correction separates viewer reconciliation from health updates and
caches the last progress. During death, viewers still follow entity tracking;
returning observers regain the same bar with its cached progress. Actual corpse
removal clears the remaining audience. Star-drop paths are unchanged.

Official 26.3 `WitherBoss.startSeenByPlayer` and `stopSeenByPlayer` manage viewers
through the `ServerEntity` pairing hooks. `LivingEntity.tickDeath` removes the
corpse at death tick 20. Dying mobs skip `serverAiStep`, retaining the Wither's
last progress. Pairing continues during the animation; it can restore the corpse
and its bar to an observer who returns before removal.

The focused regression is `fixtures/wither-death-bossbar/cases.json`, checked by
`tests/check_wither_death_bossbar.py` using actual isolated arenas and a connected
protocol-777 observer. Two trials cover active, charging, NoAI-after-tracking,
and observer departure/re-entry for active and charging bosses. Each samples
death ticks 0, 1, 4, 7, 19, 20 and 21. Checks correlate one identified Wither's
spawn, zero-health metadata and removal packets with one bossbar UUID, viewer
membership and retained progress. Initial health, bounded boss position, exact
observer positions, client survival, empty arena, cleanup and shutdown are
controls. Each target executes identical commands and 556 controlled ticks.

Official vanilla and patched Pumpkin each pass 484/484 focused checks. The
campaign79 baseline passes 448/484, failing exactly 36 assertions for early bar
removal or missing re-entry. All other controls pass. The short departure to
X=-18 preserves chunk availability for prompt return tracking. Exploratory
captures with inadequate chunk re-entry readiness, corpse-selector queries or
an interrupted observer run are excluded from these results. Integral/decimal
SNBT formatting is compared numerically.

Workspace formatting, all 450 core Rust library tests, core Clippy with all
targets/features, and the debug server build passed under the shared Cargo lock,
one build job, disabled debug information/incremental compilation and required
memory/CPU limits. The existing `proc-macro-error2` future-compatibility notice
remains. Source, binary, fixture, checker, probe, reference-source, report and
packet/log hashes were verified; final server/client logs contain no errors or
panics. Runtime evidence: `artifacts/jaron-wither80-live-validation.json` and
`artifacts/jaron-wither80-final-rust-validation.json` in the deployment workspace.

Source baseline: campaign79 `2f8d5b3ca7e621a418321d23a8c1a65e2b9a3c88`.
Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor.
Upstream master `9c04f714bb7eb26579c652f9744895d465ee902b` retains early cleanup.
All 323 current open PRs were inspected. PR3865 changes death loot but retains
immediate bossbar removal. Merged PR4092 also retains it despite introducing a
progress cache and AI changes; this correction addresses the remaining lifetime
and viewer behavior.

This is headless server/protocol evidence, without rendered-client, Bedrock,
natural boss fight or whole-fight proof. Existing initial NoAI audience scheduling,
shared tracking behavior, corpse movement and loot timing remain outside the
correction. No separate upstream-master binary was built. The focused regression
exercises the real world/tracker/observer paths rather than a mocked Rust setter.

For a human play test in a disposable arena, summon a Wither, wait for its bar,
then kill it with generic_kill damage. Expect the bar to retain its last progress
through the death animation and disappear with the corpse. Repeat during
charging and with NoAI enabled after the bar appears. Leave tracking range during
the animation: expect the bar to disappear and return with its last progress on
re-entry before corpse removal. Capture: a real-client recording is still needed
before any human PR.
