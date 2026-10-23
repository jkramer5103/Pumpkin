# Wither flight waypoints

A Wither pursuing a lower target initially climbed in Pumpkin. In the bounded
arena, official Minecraft 26.3 first produced vertical velocity
`-0.01176000043332576`, while the campaign-87 binary produced
`+0.01176000043332576`. The same frozen-tick fixture, probe and real headless
protocol-777 observer reproduced the difference twice. This is a navigation
error separate from the no-gravity correction in campaign 87.

Vanilla `FlyingPathNavigation.tick` calls the inherited `followThePath` and then
uses `Path.getNextEntityPos`. Arrival compares X and Z separately against a
width-dependent margin and Y against one block, measured from the node's bottom.
The movement destination also uses that bottom Y, with a width-dependent X/Z
offset. Pumpkin instead used a radius-0.5 sphere around the block center, then
aimed half a block above the node. Its rounded-up start node was not considered
reached, so descending pursuit first steered back up to that node.

The correction uses the vanilla arrival bounds, the existing corner-direction
helper with vanilla's dangerous-node exclusions, and the existing
`Path.get_next_entity_pos` for the movement destination. Only Wither constructs
a flying navigator in this checkout. Navigation still applies movement through
this branch's existing mechanism; controller installation, search/recomputation,
passenger eligibility, direct-movement ray tests, stopping and general AI timing
are outside this correction. The existing direction helper lacks vanilla's
clear-movement shortcut; this patch does not establish arbitrary route parity.

This is an attributed narrow integration of the flying waypoint correction in
[MegalithOfficial's PR #4174](https://github.com/Pumpkin-MC/Pumpkin/pull/4174),
head `07d07eed2037cbb7594a4b41530f607002b8fe71`, adapted to this campaign branch's
navigator API. It does not adopt that PR's allay implementation or broader AI
changes. PR #3955 concerns search budgets and caching instead. The deployment's
`ops/FORK.md` permits useful existing-fix integrations. No upstream PR, issue or
comment was created.

Two Rust regressions exercise the actual path-following helper: a descending
route must leave its start node and select the lower waypoint; arrival tests
cover independent horizontal axes, exact vertical boundaries and larger widths.
The existing `wither-flying-control` fixture and checker retain the complete
374-check flight matrix, including descent. The new before-fix run passed
350/374; both official and final-source Pumpkin passed 374/374. Descent, climb,
charging and NoAI vertical samples now match the official oracle within 1e-6.
Both Rust regressions failed with the old spherical arrival logic temporarily
restored, then passed with the correction. All 452 core library tests, workspace
formatting, core all-target/all-feature Clippy and the debug server build passed
under the shared Cargo lock, one build job, disabled debug info/incremental and
the prescribed memory/CPU caps. The first formatting check failed and was
corrected before the final passing validation; it is not counted as a pass.

All three runtime runs used identical probe, fixture and gameplay-command hashes,
four cases twice and 306 controlled ticks per target. Actual no-gravity metadata,
Wither tracking, boss/target health, spawn timer, client/player presence, bounded
motion, cleanup and stopped-process controls pass. No error or panic appeared in
the successful server/client logs. Source, binary, official classes, oracle,
checker, client, report, packet and log hashes are recorded in deployment
artifacts. The existing proc-macro-error2 future-compatibility warning remains.

This covers ten sampled flight ticks per case. Obstacles, arbitrary routes,
passenger eligibility, stopping and long-term AI cadence remain unverified. The
larger-width arrival bounds have Rust coverage; runtime coverage uses a default-
width Wither. The baseline binary is the provenance-verified campaign-87 build.
Fetched upstream retains the spherical arrival test, but a separate upstream-
master binary was not built.

Raw official source, jars, clients, worlds, binaries, logs, packets and probes
remain outside the repository in assignment-88 deployment artifacts. Runtime
observations are server-state and headless protocol evidence, not rendered-client
or whole-fight proof. A human can repeat the lower-target pursuit in a disposable
arena and observe that the initial movement descends instead of climbing first.
