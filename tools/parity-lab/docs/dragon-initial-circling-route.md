# Dragon initial circling route

Pumpkin initialized flight nodes by also selecting a random destination and
storing a route. A freshly circling dragon consumed that unrelated route before
choosing a holding-pattern leg. Vanilla 26.3 EnderDragon.findClosestNode only
builds the graph; DragonHoldingPatternPhase chooses its own path. Raised outer
nodes exposed fresh Pumpkin dragons climbing while vanilla descended.

The correction removes graph initialization's path assignment and its unused
random-destination helper and target_node field. Node coordinates, terrain
sampling, initialization lifetime and the phase implementations are preserved.
Both callers, ai_step and find_closest_node_to, now initialize only the graph.
No shared entity or combat code changes.

The focused regression is
[dragon-initial-circling-route.json](../lab/examples/dragon-initial-circling-route.json),
with captured output checked by
[check_dragon_initial_circling_route.py](../tests/check_dragon_initial_circling_route.py).
A connected headless protocol client observes an isolated flat overworld. Two
trials compare 16 fresh circling dragons at Y160, four dragons initialized during
hovering at Y200, and a NoAI control. Dragons are separated by 28 blocks to avoid
mutual contact. Outer-ring columns at Y240 expose unrelated routes while legal
inner nodes remain below the dragons. The heights keep intended vertical steering
saturated across horizontal route choices. Only vertical
displacement is compared; random horizontal trajectories are unconstrained.
Phase, population, exact tick advancement and NoAI controls are included.

All 489 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and a debug server build passed under the shared Cargo lock and resource
limits. Only the existing proc-macro-error2 future-compatibility notice remains.
The regression exercises real world initialization, phase routing and movement;
no isolated predicate test was added because it would miss the removed mutation.

The final immutable fixture passes 49/49 checks on vanilla and patched Pumpkin.
Baseline passes 31/49, with exactly 18 fresh-dragon position failures and no other
failed controls. Each of 32 patched first-tick heights matches vanilla:
159.99399999976157. The affected baseline dragons instead reach
160.00600000023843. Baseline failure counts are random; the checker requires an
observable unrelated upward route, rather than an exact random count. Nine
controlled ticks run per target. Source, copied-binary, fixture and stimulus hashes
were verified, all scratch servers stopped, both Pumpkin saves completed, and
server/client logs contain no errors or panics. The vanilla final-save completion
marker was not confirmed within shutdown grace; its process stopped.

Earlier exploratory probes are excluded: overlapping bosses caused mutual
contact, unsaturated warmed steering confounded one control, and an incorrect
expected last decimal digit stopped the following comparison. These setup
corrections made no additional Rust changes; captured logs remain outside Git.

Fresh upstream source and open dragon/holding-pattern/node PR searches show no
matching correction. PR3407/3661 multipart/crystal work and PR3835 projectiles are
separate. Fork master was fetched and is already an ancestor of this branch.
The [parity tracker](https://pumpkinmc.org/tracker/) and
[Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) are
investigation leads, not proof.

Limitations: headless protocol/server-state evidence only. No rendered-client
capture, exact horizontal route, live-crystal End fight, graph reinitialization
arena or whole-fight proof. Initial circling direction, phase-choice probability,
vertical-collision support and unreachable-path reconstruction remain separate
candidates requiring their own reproduction. A real-client follow-up should watch
a fresh dragon enter circling in an isolated arena with raised outer flight nodes.
