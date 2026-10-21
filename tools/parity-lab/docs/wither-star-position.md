# Wither nether-star spawn position

Vanilla 26.3 `WitherBoss.dropCustomDeathLoot` calls
`Entity.spawnAtLocation` with no offset. That creates the star at the boss's
exact X, Y and Z. Pumpkin instead passed the boss's integer block position to
`World.create_item_drop`, which randomizes each coordinate for block loot and
subtracts half an item's height from Y. The star could appear beside or below
the dead boss, including across a block boundary at negative coordinates.

The Wither now uses `World.create_item_drop_at` with its actual position. The
new helper contains the existing cancellable `ItemSpawnEvent` and item
construction. Block drops still compute their existing randomized position
before calling that helper. The star retains its extended lifetime and default
pickup delay. This patch does not change when loot drops or its gamerule gate.

Sources inspected locally: official 26.3 `WitherBoss.dropCustomDeathLoot`,
`Entity.spawnAtLocation(ServerLevel, ItemStack, Vec3)` and the `ItemEntity`
constructor. Fork master was fetched and is already an ancestor of this branch.
Upstream master `44d881c32` retains block-position star drops. Open upstream
PR 3865 addresses death timing and PR 4105 addresses `mob_drops`; neither
corrects the position. PR 4092's AI/lifecycle changes remain deferred. The
tracker's spawn-window goal is already implemented by an earlier campaign fix.

Regression inputs are in `fixtures/wither-star-position/cases.json`. In an
isolated, frozen arena, kill a NoAI Wither at each listed position and read the
nether-star NBT immediately and after one completed simulation tick. Select
only the pristine `Age:-6000s` sample; its `Pos` must equal the boss position
exactly. Do not infer the spawn position from a moving item. Repeat twice.
`tests/check_wither_star_position.py` checks the raw NBT samples against the
fixture and rejects the baseline reports with the six expected position failures.
Nonlethal damage must produce no item. The protocol 777 headless client keeps
a player in the arena; NBT is the position oracle, not client rendering or
packet arrival timing. Ordinary block-drop placement was reviewed in source;
a proposed `/setblock ... destroy` control was excluded because its existing
Pumpkin implementation suppresses item drops. That command behavior is outside
this boss patch.

All 450 `pumpkin-core` Rust library tests, workspace formatting, core
all-target/all-feature Clippy and the debug server build passed under the shared
Cargo lock, one build job, disabled debug info/incremental compilation and the
required 5 GiB/zero-swap/200% CPU scope. The existing `proc-macro-error2` future
compatibility notice remains. Vanilla and patched Pumpkin each pass 68/68 checks; the campaign 71
baseline passes 62/68 with exactly six wrong spawn-position failures. Two trials
cover fractional coordinates, negative coordinates, a block-center position and
a nonlethal control, using identical command streams and 261 verified ticks per
target including setup and cleanup. All six lethal patched samples match the
vanilla position exactly while still at age -6000 and pickup delay 10. Each
headless client stays connected, each arena is cleaned, and each scratch server
is stopped. Final console/client logs contain no ERROR, panic or uncaught-thread
exception lines. Source, fixture, checker, probe and copied-binary hashes are
recorded in the local validation artifacts.

Limits: these tests isolate drop placement with command-triggered deaths. They
do not prove a natural fight, live plugin cancellation, a rendered client,
Bedrock, world reloads, death timing or `mob_drops` parity. The live baseline is
the previous campaign 71 binary, not a separately built upstream master.
