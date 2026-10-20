# Dragon failed and partial flight routes

Assignment 58 investigates EnderDragon.findPath search exhaustion, separate from
normal landing approach progression fixed in assignment 57.

Vanilla 26.3 tracks the closest popped node to the requested graph destination.
If search cannot reach the destination, it returns null when no node improved on
the starting node, otherwise reconstructs the closest reached route. An optional
podium node is appended only to a successful or partial route.

Pumpkin reconstructs from the requested destination regardless of whether it was
reached, yielding a synthetic direct hop to an unreachable outer node after
crystal loss. LandingApproach also unconditionally appends the podium, so a failed
search can drive movement and advance descent.

The isolated fixture deliberately clears the podium column in the Overworld:
heightmap target lookup then falls back to node 0, while traversal with no End
fight may only add nodes 12 through 23. Dragons starting nearest node 12 cannot
improve their distance to node 0; a dragon starting near node 16 has a valid
partial route toward node 12. Restoring the podium supplies a reachable control.
NoAI, hovering, presence, precise tick counts and cleanup are also checked.

The refined arena passed 34/34 checks on vanilla and 29/34 on baseline Pumpkin
(commit 11649f4cf), including the checker's additional five-boss presence check.
The baseline failed exactly four stationary/zero-motion checks for the two failed
routes and one partial-route phase check. After three ticks, vanilla remained at
(40,90,0)/(40,120,0) with zero motion; Pumpkin moved both by about 0.35 blocks.
After one forced distant-target decision the partial-route dragon remained in
approach on vanilla but entered descent on Pumpkin. Reachable-podium recovery,
NoAI, hovering, phase/presence, 54 controlled ticks and cleanup passed.

The first exploratory arena had implicit summon centering and overlapping
dragons; it is retained locally and excluded. Refined evidence is recorded in
artifacts/christine-dragon58-before-validation.json in the deployment workspace.

The Rust fix returns None for a search that makes no progress, or reconstructs the
closest reached node for a partial path. The unused final_node heuristic argument
is removed: graph search always aims at the requested graph node, while the
landing phase appends its off-graph podium only if graph search returns a route.
Circling, takeoff and strafing callers map failed searches to their existing empty
route state. A focused Rust regression covers partial/no-progress, already-at-goal
and crystal-present reachability cases. The arena fixture and checker reproduce
the observable behavior.

Final validation passed: 490 core Rust library tests, workspace formatting,
core all-targets/all-features Clippy and a debug Pumpkin server build, serialized
under the shared Cargo lock with one build job, debug info/incremental disabled,
5 GiB memory/no swap and a two-CPU quota. Commands were `cargo fmt --all -- --check`,
`cargo test --locked -p pumpkin-core --lib`,
`cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
`cargo build --locked -p pumpkin`.

The identical final five-dragon fixture passed 34/34 checks on vanilla and patched
Pumpkin; the baseline failed exactly the original five checks (29/34). Both
no-progress dragons stayed at their exact positions with zero motion after the
fix, the partial route continued before descent, and reachable-podium recovery
passed. Source/fixture/stimulus/copied-binary hashes, connected headless clients,
stopped scratch servers and clean server/client logs were checked. Both Pumpkin
saves completed. Vanilla's final-save completion marker was not confirmed within
the shutdown grace; its process stopped. The existing proc-macro-error2 future
compatibility notice remains.

The final driver's first assertion pass rejected the four correct stationary
values because it expected textual `40.0d`/`0.0d`, while Pumpkin emitted
`40d`/`0d`. The focused checker now parses numbers and recomputes all four
movement/velocity checks from every target's unchanged raw responses. Rechecking
the preserved report passed; neither the Rust source nor arena stimuli changed.
Evidence is in artifacts/christine-dragon58-rust-validation.json,
artifacts/christine-dragon58-live-validation.json and
artifacts/christine-dragon58-format-check-correction.json in the deployment
workspace.

No rendered-client, whole-fight, crystal-present fight, survival target selection,
or vertical-collision parity claim. Numeric precision and heap ties remain outside
this patch. Multipart/damage/despawn and projectiles overlap PR3407/3661/3835 and
are deferred. Open upstream diffs do not change this flight-path search.

Human play test: in an isolated arena with no active End fight and an empty
podium column, enter landing approach near (40,90,0), expect no target steering;
enter from (-40,90,0), expect a partial route before descent. Restore a podium at
y79 and re-enter from (40,90,0), expect immediate descent. Capture the trajectory
and phase progression with a rendered client before considering an upstream PR.
