# Dragon flight node terrain height

Dragon flight nodes now use the first space above motion-blocking terrain,
excluding leaves, as vanilla 26.3 does. Pumpkin previously sampled the top
motion-blocking block itself and included leaves. The one-block offset changed
nearest-node selection at a real boundary, and leaves could raise the flight
route. The existing 73-block floor and five/fifteen-block ring offsets remain.

Only `EnderDragonEntity::ensure_nodes_initialized` changes. Takeoff, circling
and strafing all use its cached nodes. Coordinate rounding, graph search,
random route initialization and phase policies are separate candidates.
No shared entity or world code changes. No plugin event is removed or bypassed.

Vanilla reference: `DragonTakeoffPhase.findNewTarget` calls
`EnderDragon.findClosestNode`, which initializes nodes through
`LevelReader.getHeightmapPos(MOTION_BLOCKING_NO_LEAVES, ...)`.
`Level.getHeight` adds one to the chunk's top-block height; Pumpkin's heightmap
helper returns the top block. The Rust correction selects the corresponding
heightmap and adds that one block. Local source/jar hashes and upstream overlap
searches are retained outside Git. Fork master was fetched and already integrated.
Open dragon/node searches and PR3407/3661/3835 contain no corresponding correction.
The tracker/issue3468 multipart collision lead is already handled or overlaps
existing upstream work, so this patch addresses a separately reproduced AI defect.

The focused regression is
[`dragon-flight-node-height.json`](../lab/examples/dragon-flight-node-height.json).
It runs two trials each with a bedrock roof and a leaf roof at Y160 in a scratch
overworld without an End fight or crystals. At X55.5/Y120, yaw90, the solid-roof
case distinguishes node heights 176/166 from 175/165: vanilla starts climbing,
while old Pumpkin stays still. With leaves and X50.5, vanilla stays still at
yaw90 and descends at yaw0, while old height sampling gives an elevated route.
Other positions and NoAI cases control for ordinary ascent, stationary paths
and AI suppression. The fixture disables random ticks and checks leaf columns
before and after the trials. Frozen tick deltas and numeric position/motion
observations are checked with a connected headless protocol client.
Random horizontal routes are deliberately unasserted.

All 485 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared Cargo lock and resource
limits. The identical final fixture passes 100/100 primary checks on vanilla and
patched Pumpkin and 94/100 on baseline Pumpkin, with exactly six expected movement
failures. Supplementary numeric position, motion and preparation controls bring
vanilla and patched results to 224/224; baseline retains the same six failures.
The corrected first-tick vertical positions and velocities match vanilla.
Each target advances 80 controlled ticks.

Fixture, stimulus, source and copied-binary hashes match. Connected headless
clients, arena cleanup and stopped scratch servers are verified. Both Pumpkin
saves completed; server/client logs contain no errors or panics. Vanilla's final
save-completion marker was not confirmed within shutdown grace; its process stopped.
Existing development/debug, offline-mode, Java native-access/deprecation and
proc-macro-error2 future-compatibility warnings remain.

Initial exploratory leaf-state syntax was rejected by Pumpkin's block argument
parser; that report provides no leaf proof. A separate initial expectation
incorrectly described the yaw0 leaf control as ascent; vanilla descends because
its selected nodes are below 120. Only reports with the final fixture hash count
as before/after evidence.

Limitations: no rendered-client capture, natural launch, crystal-present arena
or complete boss-fight proof. Node coordinate truncation, graph search, lazy
route seeding and circling decision timing remain separate leads.
