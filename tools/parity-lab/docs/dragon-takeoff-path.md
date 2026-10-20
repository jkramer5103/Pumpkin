# Dragon takeoff path target

Pumpkin's first takeoff tick aimed at the fixed point `(fightOrigin.x, 105,
fightOrigin.z)`. Vanilla 26.3 chooses a flight path using the dragon's head look
vector, skips the path's starting node and targets the next node with a random
vertical offset. In a bounded arena below raised flight nodes, vanilla therefore
rises while the old Pumpkin code descends toward Y=105.

The correction selects a look-relative destination, applies the existing
crystal-dependent ring selection and graph search, and targets the first
remaining path node. Pumpkin's path helper already omits the starting node.
Takeoff entry clears the previous shared path and target; subsequent phase
completion retains the earlier ten-block podium-boundary correction.

Reference call chain: `DragonTakeoffPhase.begin` / `doServerTick` /
`findNewTarget` / `navigateToNextPathNode`, `EnderDragon.getHeadLookVector`,
`findClosestNode`, `findPath` and `aiStep`. Local decompiled 26.3 source and jar
hashes are retained outside Git in the assignment48 provenance artifact.

The focused world regression is
[`dragon-takeoff-path.json`](../lab/examples/dragon-takeoff-path.json). Two trials
observe the first takeoff tick at four headings, repeated entry from hovering,
and NoAI controls. The platform raises every flight node sufficiently that its
random vertical offset cannot change the sign or clamp of vertical steering.
The fixture checks vertical movement; horizontal routes remain unconstrained.
It uses an isolated scratch world and a connected headless protocol client.
This world-dependent regression is retained instead of a mock of the dragon,
world, heightmaps and phase manager.

The identical final fixture passes 71/71 primary checks on vanilla and patched
Pumpkin and 55/71 on the baseline, with exactly sixteen expected active
vertical-position failures. Roof preparation and NoAI controls pass. Each target
advances 68 controlled ticks. Numeric position/motion and setup controls bring
vanilla and patched totals to 127/127; all sixteen patched vertical
position/velocity pairs agree with vanilla. Baseline reports 79/95, retaining
its expected position failures and separately confirming downward velocity.

Final Rust validation passed all 482 core library tests, workspace formatting,
core all-targets/all-features Clippy and the debug server build under the shared
Cargo lock and resource limits. Node-height addition uses float before conversion
to double, as in vanilla. Fixture, stimulus, source and copied-binary hashes match.
Connected headless clients, cleanup and stopped scratch servers are verified.
Both Pumpkin saves completed; server and client logs contain no errors or panics.
Vanilla's final-save marker was not confirmed within shutdown grace; its process
stopped. The final float-rounding revision has its own passing Rust record and
copied-binary arena report. Earlier binaries are excluded from final patch proof.

Exploratory reports with a mistyped expected float, unloaded roof edge chunks and
text-only integer-double NoAI checks are excluded. The retained fixture uses a
bounded load wait and explicit positive roof checks. Existing development/debug,
offline-mode, Java native-access/deprecation and proc-macro-error2 future
compatibility warnings remain.

Fresh upstream dragon/takeoff searches and PR3407/3661/3835 file diffs show no
corresponding takeoff path correction. Fork master is already an ancestor of
this branch; no integration commit is needed. The tracker and mob-AI issue are
leads; their earlier contact/collision findings were not repeated.

Limitations: no rendered-client capture, whole-fight proof, natural perched
launch sequence, crystal-present route or exact horizontal path validation.
The shared node coordinates, heightmap choice/offset, nearest-node filtering and
path search remain existing approximations and require separate reproduction.
The current patch uses Pumpkin's existing yaw/pitch vector utility; it does not
replace that utility with vanilla's trigonometric lookup. Multipart registration,
crystal healing and projectile overlap remain separate work.
