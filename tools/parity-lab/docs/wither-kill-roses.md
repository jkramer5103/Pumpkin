# Wither kill-credit roses

Pumpkin does not create wither roses when a Wither kills a living entity. Java 26.3 plants a rose at the victim's block position when mob griefing is enabled, the position is air and the rose can survive there. Otherwise it spawns one rose item at the victim's exact position with no pickup delay. Neither path depends on `mob_drops`.

The fix adds `LivingEntity::create_wither_rose` to the existing once-only death flow after equipment drops. It uses kill credit independently of ordinary death loot and reuses the registered rose placement rules. Item fallback preserves `ItemSpawnEvent` cancellation and the normal entity-spawn event.

Reference: official local 26.3 `LivingEntity.die`, `getKillCredit`, `createWitherRose`, `ServerPlayer.die`, and `ItemEntity` constructor. Fork master was fetched and is already an ancestor. Current upstream has no rose creation; open PR3865 moves the separate nether-star death drop and PR4105 gates ordinary loot on `mob_drops`. Direct skull-hit attribution belongs to open PR3835 and remains outside this patch.

## Regression and validation

`lab/examples/wither-kill-roses.json` uses a bounded loaded arena, a creative headless observer, frozen simulation and credited damage. It covers dirt and soul-soil planting, unsuitable bedrock support, occupied water, independent disabled gamerules, a zombie killer and a surviving cow. Fallback checks require exactly one rose, exact initial position, age zero and pickup delay zero, including a second damage attempt against the corpse. Each case clears items after block changes, which can dislodge a preceding planted rose.

Existing external protocol-777 tooling also captures a naturally fired owned Wither skull, pauses its shooter, and drives the skull into bedrock beside a 1-HP cow. It verifies a clean initial item state, projectile consumption, splash death, rose creation, wall preservation, client survival and cleanup in two trials per target. Victim health and roses are command-observed. Packet evidence records the bosses and fired skulls; cows killed during frozen simulation are absent from spawn-packet evidence.

Final identical-fixture comparison: vanilla and patched Pumpkin pass 150/150 checks; baseline ee2c345d passes 120/150. Its 30 failures are the expected rose placement, presence, origin and count assertions, including both natural splash kills. Repeated assertions are not independent defects. Other-killer, nonlethal, clean-arena and rule controls pass. Gameplay command hashes match after excluding read-only time queries and randomized shot-capture latency. Raw events are retained. All three scratch processes stopped; both Pumpkin logs show completed saves/stops with no server/client errors or panics. Vanilla RCON shutdown is verified; full save completion is not.

Rust verification passed under the shared Cargo lock with one job, debug information and incremental compilation disabled, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%: workspace formatting, all 444 existing core library tests, core all-targets/all-features Clippy and a debug server build. Source and copied-binary hashes match the live test. The existing proc-macro-error2 future-compatibility warning remains. Focused regression coverage is the live fixture; no new Rust unit test is added for this world-dependent behavior.

Local evidence: `artifacts/jaron-wither43-validation.json`, `artifacts/jaron-wither43-verify.json`, `artifacts/jaron-wither43-source-provenance.json` and `artifacts/jaron-wither43-overlap-final.json`. Investigation scripts and runtime artifacts remain outside the commit.

## Limits

No rendered Java/Bedrock client, multiplayer, player victim, world reload, live plugin-listener cancellation or full boss fight was tested. Direct skull hits currently omit living-shooter context in Pumpkin; this patch does not claim that upstream projectile issue is fixed. Existing kill-credit expiry and player-priority behavior are reused.

For a human play test, let a Wither kill mobs on dirt and bedrock, then with mob griefing and mob drops independently disabled. Expect planted roses on suitable air positions when griefing is enabled, and item fallbacks otherwise. Capture the results with a real client before any upstream submission.
