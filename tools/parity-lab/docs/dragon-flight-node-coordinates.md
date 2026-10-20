# Dragon flight-node coordinates

The dragon previously generated flight-node columns with direct trigonometry and
integer truncation. Vanilla uses lookup-table trigonometry, a shifted float angle
and floor. In particular, its negative diagonal middle-ring node is (-29, 28),
while Pumpkin used (-28, 28). This changes which node is closest and whether a
fresh takeoff has a path target.

The correction uses the existing pumpkin-util sin/cos lookup helpers and matches
vanilla's float expression and floor. Ring radii, height adjustments, fight-origin
translation, node caching, and phase entry behavior remain as before. Circling,
strafing and takeoff all consume the corrected cached columns. No shared combat
or world files change.

Reference: Minecraft Java 26.3 EnderDragon.findClosestNode, DragonTakeoffPhase's
findNewTarget/navigateToNextPathNode, Mth.sin/cos/floor and EnderDragon.aiStep.
All 24 expected coordinate pairs in the Rust regression were extracted by calling
the actual vanilla server Mth class. The source and extracted output are retained
outside Git with hashes. Fresh upstream master, open dragon/node searches and
PR3407/3661/3835 were checked; none contains this node-generation correction.
Fork master was fetched and is already integrated. The
[Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[tracker](https://pumpkinmc.org/tracker/) were treated as leads; the earlier
collision gates are already fixed or overlap the existing multipart work.

The focused fixture is
[`dragon-flight-node-coordinates.json`](../lab/examples/dragon-flight-node-coordinates.json).
It uses a frozen, isolated flat overworld, no fight or crystals, and a connected
headless protocol client. Two trials exercise first takeoff at floor query X=-44,
Z17/18/19, Y120 and yaw225, with a Z18 NoAI control. The final comparison shows
vanilla stays at (-43.5, 120, 18.5) at Z18 while baseline Pumpkin descends to
Y119.99399999976158 and moves horizontally. Both descend at Z17, stay still at
Z19, and remain stationary with NoAI. Exact random horizontal values are unasserted.

All 486 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared Cargo lock/resource limits.
The coordinate regression fails with the original formula restored and passes with
the correction. The identical final fixture passes 35/35 primary checks on vanilla
and patched Pumpkin; baseline passes 33/35 with exactly the two expected Z18 movement
failures. Numeric position/motion and preparation controls bring vanilla and patched
results to 95/95. Each target advances 56 controlled ticks. The corrected stationary
positions and zero motion match vanilla exactly; moving controls match vertical
position and motion, while randomized horizontal magnitudes remain unasserted.

Fixture, stimulus, source and copied-binary hashes are verified. Connected headless
clients, entity cleanup, force-load cleanup and stopped scratch servers are verified.
Both Pumpkin saves completed; server/client logs contain no errors or panics.
Vanilla's final save-completion marker was not confirmed within shutdown grace;
its process stopped. Existing debug-build, offline-mode, Java native-access/deprecation
and proc-macro-error2 future-compatibility warnings remain. The temporary old-formula
negative control also emits unused trig-import warnings; the corrected source does
not add Clippy warnings.

The initial fixture expected vanilla's numeric string 120.0d; Pumpkin prints 120d.
The final fixture accepts both representations, and numeric comparisons verify
state separately. Initial substring-only control failures are excluded.

Limitations: headless state evidence only; no rendered-client capture, natural
launch, crystal-present arena or complete boss-fight proof. Path graph search,
lazy initial random routing and circling decision timing remain separate leads.
