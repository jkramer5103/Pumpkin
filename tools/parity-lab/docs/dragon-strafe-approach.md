# Dragon strafe approach path

When a circling dragon selected a player for strafing, Pumpkin stored only the
player ID. It immediately steered at the player instead of following vanilla's
initial graph route and final player waypoint. The new `StrafingPhase.set_target`
builds that route, consumes its first hop and appends an off-graph node at the
player's block X/Z and the floored height offset. The strafe phase owns its path;
phase entry resets the target and path. Only a completed path enables direct
player tracking. Orbit direction and attack eligibility keep their behavior.

The reference is Minecraft Java 26.3 `DragonHoldingPatternPhase.strafePlayer`
-> `DragonStrafePlayerPhase.setTarget` -> `EnderDragon.findPath` ->
`navigateToNextPathNode`, followed by `doServerTick` and dragon steering.
Pumpkin's graph search already omits the starting node, so initialization must
not advance past another graph hop. Failed searches remain absent, distinct
from completed routes. Waypoint height jitter uses vanilla's float arithmetic.
The phase manager's typed strafe accessor refers to the same instance it ticks.

A Rust regression covers graph hops followed by the terminal player node,
same-node routes, and failed searches. The focused live fixture is
`fixtures/dragon-strafe-approach/cases.json`, with report assertions in
`tests/check_dragon_strafe_approach.py`. It normalizes eligible flight-node
columns before node initialization, acquires a target naturally with 16 dragons
at Y245 and a protected survival player at Y140, then retains only one dragon.
Two trials each reset position, velocity and yaw before five one-tick samples.
The retained player is behind the dragon to prevent its fireball attack.
A far sample advances the remaining terminal node; two further samples check
direct tracking after approach completion. NoAI supplies a stationary control.
Position, motion, phase, health, loaded clear space, terrain, tick deltas, client
presence and cleanup are checked. All worlds and servers are isolated scratch
instances under the shared engine lock.

Discovery: `artifacts/christine-dragon64-low-approach-live-20261020T222720.529309Z/report.json`.
Vanilla's ten initial samples descend with velocity Y `-0.005460000374317176`;
campaign63 baseline's ten samples instead produce `-0.00006825000015894567`.
The initial Y300 acquisition experiment is excluded: it makes the baseline
select a new orbit before observations and masks the initialization defect.
The accepted reference/baseline report is
`artifacts/christine-dragon64-final-live-20261020T222929.421860Z/report.json`;
the patched report is
`artifacts/christine-dragon64-final-live-20261020T223514.349278Z/report.json`.

| Target | Response checks | Controlled ticks |
| --- | ---: | ---: |
| Vanilla | 16/16 | 18 |
| Campaign63 baseline | 2/16 | 18 |
| Patched | 16/16 | 18 |

The fourteen baseline failures are ten initial approach responses and four
responses after advancing the terminal waypoint. Vanilla and patched retain
the approach before that advance, then enable direct tracking; the baseline
starts direct tracking and instead creates an orbit when forced far away.
Both NoAI controls pass. Controlled command hashes match across all targets.
All six server/client logs passed the error scan, and scratch servers stopped.

Workspace `cargo fmt --all -- --check`, `cargo test --locked -p pumpkin-core
--lib` (492 passed), `cargo clippy --locked -p pumpkin-core --all-targets
--all-features`, and `cargo build --locked -p pumpkin` passed under the shared
Cargo lock with one job, no incremental/debug info and the required systemd
memory/CPU limits. The existing proc-macro-error2 future-compatibility notice
remains. Raw Rust results are in
`artifacts/christine-dragon64-rust-validation.json`; checked live results are in
`artifacts/christine-dragon64-live-validation.json`; source, official-JAR and
copied-binary hashes are in `artifacts/christine-dragon64-source-provenance.json`.

Fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an
ancestor of this branch. Upstream `44d881c3215692df498182f770ed83fcc426df1f`
retains the missing approach initialization. Fresh open-PR searches and file
reviews of #3407, #3661, #3835 and #4080 show multipart, healing, despawn,
projectile and contact/team foundations, which remain deferred. No upstream
patch was copied. The [tracker](https://pumpkinmc.org/tracker/) and
[mob AI issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) are leads;
their old collision gates have already received separate campaign fixes.

The baseline is the current campaign commit
`8e835f41f663fbfa9218778f94724d4ffbc27c9f`, not a separate upstream-master
binary. Evidence is headless protocol777/server state with controlled teleports;
it does not prove rendering, a natural full trajectory, Bedrock or a whole
boss fight. A human client check should record a dragon acquiring a player and
following approach waypoints before direct pursuit. No visual result is claimed.
