# Dragon flight paths after crystal loss

Pumpkin's dragon path search previously expanded outer-ring nodes even without
live crystals. Vanilla EnderDragon.findPath starts neighbor expansion at node 12
when its fight is absent or has zero surviving crystals. This differs from the
already-corrected nearest-node lookup: selecting middle-ring endpoints alone
does not prevent the graph search from detouring through the outer ring.

The Rust correction passes the live crystal state into each dragon path search:
initial flight routing, circling, strafing and takeoff. Only neighbor expansion
changes. Starting-node handling, costs, graph edges, reconstruction and phase
steering stay as before. With live crystals, all 24 neighbors remain eligible.
No shared living, combat or world files change.

Reference: Minecraft Java 26.3 DragonTakeoffPhase.findNewTarget and
navigateToNextPathNode, EnderDragon.findPath and aiStep. The existing cached node
columns and heights are used. Fork master was fetched and is already integrated.
Fresh upstream source and open dragon/path/node searches were reviewed;
PR3407/3661 cover multipart behavior and PR3835 covers projectiles, with no
matching graph-neighbor restriction. The
[Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[tracker](https://pumpkinmc.org/tracker/) were treated as leads; their contact
items are already corrected or overlap the deferred multipart changes.

The focused regression fixture is
[`dragon-flight-path-crystal-restriction.json`](../lab/examples/dragon-flight-path-crystal-restriction.json).
It uses a frozen, isolated flat overworld with a connected headless protocol
client and no dragon fight or crystals. Stone columns raise the intermediate
middle/inner nodes, leaving the east and south endpoints low. Two trials of the
first takeoff tick in each direction show vanilla ascending from Y120 to
120.00600000023842 while baseline Pumpkin descends to 119.99399999976158.
Both descend on the flat-route control and remain still with NoAI. Random
horizontal magnitudes are unasserted. All 56 controlled ticks and preparation,
phase, client-presence, cleanup and stop checks pass. Vanilla passes 43/43 primary
checks (95/95 including numeric controls); baseline passes 39/43 with exactly
four expected raised-route position failures. Baseline's other numeric controls
pass. Both scratch processes stop; Pumpkin completes saving. No server/client
errors or panics were found. Vanilla's final save marker is unconfirmed within
the shutdown grace period.

The focused Rust regression exercises the actual graph search in both directions
across the raised middle-ring route and its lower outer-ring alternative. It
checks the restricted route without crystals and preserves the alternative when
crystals are present.

All 487 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared Cargo lock and resource
limits. The focused regression fails with the original unrestricted neighbor scan
restored and passes with the correction. The unchanged fixture passes 43/43 primary
checks and 95/95 including numeric controls on patched Pumpkin, matching vanilla.
All four raised-route vertical positions and velocities match vanilla exactly.
Each target advances 56 controlled ticks. Fixture/stimulus/source/copied-binary
hashes, headless client readiness, cleanup and process stops are verified; both
Pumpkin saves complete. Server/client logs contain no errors or panics. Vanilla's
final save-completion marker remains unconfirmed. Existing debug/offline-mode,
Java native-access/deprecation and proc-macro-error2 future-compatibility warnings
remain. The temporary negative control's unused-variable warning does not apply
to the corrected source.

Limitations: headless protocol-client/server-state evidence only. No rendered
client, natural launch, crystal-present live arena or whole-fight proof. Existing
float/path tie handling, unreachable-path reconstruction, random initial routing
and circling decision timing remain separate leads. Multipart/crystal healing and
projectile overlap remain deferred. This bounded fix does not establish complete
boss or campaign parity.
