# Dragon crystal counts use hitbox intersections

Pumpkin's dragon fight counted a pillar crystal only when its center was inside
the pillar query box. A two-block-wide crystal can overlap a pillar query while
its center is outside. The count then incorrectly reports no surviving crystals,
which changes the dragon's flight routes and phase choices.

The correction uses the existing world hitbox query in `update_crystal_count`,
then filters for End Crystals. Per-pillar counting, the scan timer and the query
bounds remain unchanged. This matches official Java 26.3
`EnderDragonFight.updateCrystalCount` -> `EntityGetter.getEntitiesOfClass`.
`DragonTakeoffPhase.findNewTarget` and `EnderDragon.findClosestNode/findPath`
consume the count to select the outer or middle/inner flight rings.

Fork master is already an ancestor of the campaign branch. Current upstream still
uses center containment. Open dragon, spike, pillar and crystal PRs were checked;
PR3407/3661 concern multipart registration/combat and PR3694 crystal placement and
explosion damage, with no matching crystal-count fix. The tracker and Mob AI issue
3468 were reviewed as leads; already-fixed contact gates and overlapping multipart
work were excluded.

Regression coverage: `fixtures/dragon-crystal-count-hitboxes/cases.json` and
`tests/check_dragon_crystal_count_hitboxes.py` compare an isolated End fight on
official 26.3, the previous campaign binary, and the patched server. A real
headless protocol client keeps the fight active. The middle/inner flight route is
raised before the natural dragon creates its cached flight nodes. Player entry
loads the arena; single-step readiness checks freeze a new dragon immediately.
PersistenceRequired prevents unrelated random despawning during scan waits, and
each trial verifies the same dragon UUID. Each trial removes all crystals, optionally places one at a pillar boundary, lets the fight
refresh for 101 frozen/controlled ticks with dragon NoAI, then measures one
actual takeoff tick from (40,120,0), yaw180. A surviving pillar crystal permits
a low outer-ring route; without one the raised route makes the dragon ascend.
Center, absent, half-block overlap and exact-touch controls cover both sides of
X and Z. Crystal positions, scan tick deltas, flight phase, motion, player/client,
cleanup and server process stops are checked. Horizontal random magnitudes are
not asserted.

All 493 pumpkin-core Rust library tests, workspace formatting, core all-targets/
all-features Clippy and the debug server build passed under the shared Cargo lock
and resource limits. No Rust source changed after those checks. The focused live
regression passes all ten samples on vanilla and patched Pumpkin. Baseline
campaign79 has exactly four overlap mismatches: it ascends to
Y120.00600000023842 where vanilla and patched Pumpkin descend to
Y119.99399999976158. Center, absent and four exact-touch controls agree.
The same 204 stimulus commands after setup run on all three targets, with
1,020 controlled observation ticks per target. Readiness/setup durations differ
by target; total controlled ticks are 1,267 vanilla and 1,278 each Pumpkin target.
Client/player presence, crystal position, dragon persistence/UUID, scan deltas,
flight phase, vertical motion, cleanup and process stop checks pass. Server and
client logs contain no errors or panics. Source, copied binary, official jar,
probe, fixture, checker, stimulus and report hashes were verified. Existing debug,
offline-mode, Java native-access and proc-macro-error2 notices remain.

Five earlier arena setup attempts are excluded: cached flight nodes, unavailable
chunks before player entry, unsupported terminal loaded condition, silent RCON
say output, and an unprotected dragon randomly despawning. The final identical
probe uses player-first entry, observable time-query readiness, persistence and
UUID controls. These setup failures are not parity evidence.

Limitations: headless protocol/server-state evidence only; no rendered-client,
Bedrock, reload or whole-fight proof. The fixture uses command-placed invulnerable
crystals, a persistent natural dragon and elevated flight-node terrain. It covers
horizontal membership with zero/one crystal, not larger counts, phase probability
distributions or initial crystal-spawn membership. Current upstream retains center
containment in source; no separate upstream-master binary was built. Before any
future upstream submission, a human should play-test pillar-edge crystals and
record the dragon taking an outer flight route while a crystal overlaps the query.
Capture: <attach a real-client screenshot or recording here>.
