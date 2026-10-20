# Dragon strafe orbit selection

When a strafing dragon needs another flight route, vanilla selects a successor
on its orbit ring. Pumpkin searched for the player's nearest node again. If
both were nearest the same node, that search returned no hops and the dragon
continued aiming directly at the player instead of flying toward an orbit node.

The correction follows Minecraft Java 26.3
`DragonStrafePlayerPhase.findNewTarget`: choose the dragon's nearest node, flip
the phase's direction with probability 1/8 and offset six nodes on that flip,
then select the next node in that direction. With crystals, wrap around the
twelve outer nodes; otherwise wrap around the eight middle nodes. The direction
belongs to the strafe phase, starts false and persists across phase entries,
independently of the circling phase's direction. Existing path consumption and
attack checks retain their behavior. Initial strafe approach construction is a
separate limitation.

The vanilla call chain is `doServerTick` -> `findNewTarget` ->
`navigateToNextPathNode`, followed by the dragon's steering and movement.
Pumpkin's `find_path` already excludes the starting node, so the new route must
not skip it again. The one production caller of the new successor helper is
the strafe phase; the phase manager now creates its default state.

The isolated discovery arena used a connected headless protocol 777 client and
a survival player at (8,120,0). A circling dragon acquired the player naturally.
Preparation advanced the old approach and verified direct target tracking before
sampling. Each sample reset the dragon to (8,120,5), yaw 180 and zero velocity,
then advanced one simulation tick. Facing away prevented attacks from ending
the phase. In two trials, vanilla's vertical velocity was
-0.005460000374317176; baseline Pumpkin's was -0.0009782500173449514.
Vanilla moved to height 119.99399999976158; baseline moved to
119.99892500001192. All eighteen discovery samples reproduced the difference.

The Rust regression checks ring boundaries, direction and the concrete node-20
case: searching node 20 to itself yields no hops, while vanilla's orbit
successor yields a route to node 19. The world fixture at
`fixtures/dragon-strafe-orbit/cases.json` records vanilla flight observations.
`tests/check_dragon_strafe_orbit.py` checks raw reports, including a direct
approach control, two close distances and a NoAI control in each trial. It
checks target acquisition, completed approach, exact tick advancement, phase,
player health/presence, initial position/yaw/velocity, clear space, cleanup and
identical controlled commands. Adaptive preparation and read-only clock poll
counts are excluded from command hashes.

Rust validation passed: 491 `pumpkin-core` library tests, workspace formatting,
core all-target/all-feature Clippy and the debug server build. Every Cargo
operation used the shared build lock, one job, disabled debug information and
incremental compilation, and the 5 GiB/zero-swap/200% CPU limits. Initial Clippy
requested a `const` helper; that annotation was added and all checks were rerun
successfully. The existing `proc-macro-error2` future-compatibility notice remains.

The initial reference arena passed 20/20 observations on vanilla and 8/20 on
baseline Pumpkin. Exactly twelve close-distance samples failed on the baseline;
the direct approach and NoAI controls passed on both targets. Both received
twenty controlled simulation ticks with identical controlled command hashes.

The first patched arena exposed an overly specific fixture assumption: a random
direction flip can choose the farther node 17, whose randomized waypoint height
does not always cap descent from height 120. Two samples therefore had different
valid descent speeds. That run is excluded from final acceptance. The final
arena raises the player and sampled dragon to height 140. A first raised run
removed the baseline difference because the default scratch terrain differed:
Pumpkin's middle nodes were six blocks higher than vanilla's, changing the
nearest node at the higher position. That run is also excluded from differential
acceptance.

The final arena explicitly clears and sets identical terrain columns below all
twelve eligible flight nodes before summoning dragons. Each column has a
verified bedrock top at height 0, giving both servers graph nodes at height 73
and waypoints up to height 93. All possible orbit selections then cap descent,
while dragon and player have the same nearest node. The expected velocity and
numerical tolerances remain unchanged. All three targets receive the same
revised setup. The Rust source and binary remain unchanged.

The final matched-terrain arena passed 20/20 observations on vanilla and patched
Pumpkin. Baseline passed 8/20, failing exactly the twelve close-orbit samples.
Direct approach and NoAI controls passed on all three targets. Each target
received twenty controlled simulation ticks with identical controlled command
hashes. All twelve terrain-column checks, phase/player/health/clear-space and
position/yaw/motion controls passed. The copied binary and Rust source hashes
match the successful build record. All scratch servers stopped; the six
server/client logs contained no ERROR or panic lines.

| Dragon distance from player | Vanilla vertical velocity | Baseline vertical velocity |
| --- | --- | --- |
| 30, direct approach control | -0.00006825000015894567 | -0.00006825000015894567 |
| 5, new orbit | -0.005460000374317176 | -0.0009782500173449514 |
| 8, new orbit | -0.005460000374317176 | -0.0005687500096112553 |

The initial raw reference report is
`artifacts/christine-dragon63-orbit-live-20261020T220435.552633Z/report.json`.
Rust results are in `artifacts/christine-dragon63-rust-validation.json` and
source/binary provenance is in `artifacts/christine-dragon63-source-provenance.json`.
Initial approach-initialization discovery was inconclusive and excluded from
acceptance. The separate orbit discovery supplied the before-fix reproduction.
The excluded first patched report is
`artifacts/christine-dragon63-orbit-live-20261020T221630.291971Z/report.json`.
The excluded raised run with unmatched terrain is
`artifacts/christine-dragon63-orbit-live-20261020T221805.592649Z/report.json`.
The accepted final raw report is
`artifacts/christine-dragon63-orbit-live-20261020T222153.159659Z/report.json`;
checked results are in `artifacts/christine-dragon63-live-validation.json`.

The [tracker](https://pumpkinmc.org/tracker/) and
[mob AI issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) supplied leads.
Fresh open-dragon PR searches and inspection of #3407, #3661, #3835 and #4080
found overlap with multipart, healing, projectile and contact foundations, but
none with this strafe route selection. Those overlapping candidates remain
deferred. Fetched fork master is already an ancestor of this campaign branch;
relevant earlier campaign fixes are retained. Upstream master still selects
the player's nearest node in this code. No upstream patch was copied.

The live baseline is campaign commit `8c3a84b865ad7cb1117ccc0deaf71d44460d6d58`,
not a separate upstream-master build. This is headless server-state evidence,
with controlled teleports, not rendered-client or whole-fight proof. Initial
approach initialization, traveling dragon fireballs, multipart/crystal behavior
and other phases remain outside this correction. For a human play check, keep
a dragon in strafe with a close visible player and observe its subsequent
flight toward orbit waypoints; no rendered result is claimed here.
