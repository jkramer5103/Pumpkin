# Dragon nearest flight node

When there is no End fight, or its last crystal has been destroyed, vanilla 26.3
searches only flight nodes 12 through 23. Pumpkin searched all 24 nodes, allowing
an outer-ring start or destination to alter the route. The lookup now respects
live-crystal eligibility, floors the query coordinates as vanilla's pathfinder
Node does, retains the first equally near node, and preserves vanilla's strict
100-block search bound and index-zero fallback.

The correction is confined to the dragon's nearest-node lookup and its existing
initialization caller. Circling, strafing and takeoff already call this lookup;
they now receive eligible nodes. Node generation, graph search, random route
initialization and phase transition policies remain separate candidates.

Reference call chain: `DragonTakeoffPhase.findNewTarget` calls both overloads of
`EnderDragon.findClosestNode`, then `findPath` and `navigateToNextPathNode` before
`EnderDragon.aiStep` steers. Local vanilla source/jar hashes, overlap searches,
raw server reports and copied-binary hashes are retained outside Git in the
assignment49 artifacts. Fork master was fetched and was already an ancestor.
Open upstream searches and PR3407/3661/3835 file patches contain no corresponding
nearest-node correction. Earlier collision/contact fixes were not repeated.

The bounded regression is
[`dragon-nearest-flight-node.json`](../lab/examples/dragon-nearest-flight-node.json).
Two trials place a summoned dragon beside an elevated inner node ring in a
scratch overworld, with no fight or crystals. At X=60 and X=65, yaw=90, vanilla's
eligible start and destination coincide, leaving no target after the starting
node is consumed. Baseline Pumpkin instead selects an outer start and ascends.
X=50 and yaw=0 cases exercise normal ascent; NoAI cases exercise suppression.
The fixture advances frozen ticks with a connected headless protocol client.
Random horizontal routes are not compared.

All 485 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared Cargo lock and resource
limits. The three focused lookup regressions fail with the old implementation
restored. An initial Clippy numeric-suffix style error was corrected before the
final passing checks; no gameplay source changed after those checks.

The identical final two-trial fixture passes 47/47 primary checks on vanilla and
patched Pumpkin and 43/47 on the baseline, with exactly four expected movement
failures. Numeric position, velocity, phase and preparation controls bring vanilla
and patched results to 109/109; baseline retains its four expected failures.
All four corrected stationary position/velocity pairs match vanilla, as do the
ascending and NoAI controls. Each target advances 60 controlled ticks.

Fixture, stimulus, source and copied-binary hashes match. Connected headless
clients, arena cleanup and stopped scratch servers are verified. Both Pumpkin
saves completed, and server/client logs contain no errors or panics. Vanilla's
final-save completion marker was not confirmed within shutdown grace; its
process stopped.

Exploratory fixtures are excluded from final proof. X=55 lies near a tie affected
by the existing node-height offset discrepancy, so the retained ascending control
uses X=50. Stationary behavior is asserted with numeric NBT state, avoiding the
servers' `120d` versus `120.0d` textual difference. The source correction is the
same throughout these arena revisions.

Limitations: headless protocol-client/server-state evidence only, with no
rendered-client capture, crystal-present arena, natural launch or complete
boss-fight proof. Node generation still uses a different heightmap/height offset
and trigonometric rounding; graph search and lazy random route initialization
remain approximations. Existing development/debug, offline-mode, Java
native-access/deprecation and proc-macro-error2 future-compatibility warnings
remain.
