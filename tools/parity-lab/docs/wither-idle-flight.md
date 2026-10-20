# Wither idle flight

A target-free Wither stayed at the same horizontal position in Pumpkin. Vanilla 26.3 wanders through the air. In two isolated 480-tick trials, vanilla reached horizontal excursions of 14.34 and 18.08 blocks; the campaign baseline reached exactly zero in both. NoAI and spawn-invulnerability controls stayed horizontally still on both servers.

The Wither-only Rust change registers the existing `WaterAvoidingRandomFlyingGoal` at vanilla priority 5 and selects the existing flying navigator, with door opening disabled and floating enabled. The priority-0 spawn goal and priority-2 ranged goal retain precedence. No shared navigation or controller implementation changes.

## Reference and scope

The official 26.3 `WitherBoss.registerGoals` registers this goal, and `createNavigation` supplies flying navigation with these flags. The inherited `RandomStrollGoal` chooses destinations and starts navigation; `WaterAvoidingRandomFlyingGoal` selects a hover position and falls back to air/water positions. These classes were inspected from the local official jar; decompiled code is not committed.

Upstream `fb7c8e223` still lacks the Wither idle goal. Fork master `65bca3f7f` is an ancestor of the campaign branch. The tracker and Mob AI issue 3468 were reviewed as leads. Open PR 4092 changes shared AI/navigation/controller foundations but does not add this Wither idle goal or configure its flying navigator. This patch uses the current navigation interface, which writes movement input directly. It does not port that PR's controller integration. Related skull, death/drop, targeting and explosion PRs do not address this registration.

## Regression and validation

`lab/examples/wither-idle-flight.json` defines a sealed bedrock arena with a connected creative observer. It repeats target-free active movement, NoAI, and positive spawn-invulnerability cases twice. Active cases sample positions every 40 ticks over 480 ticks and require horizontal excursion above one block; the two 80-tick controls require no horizontal excursion. Presence, health, arena bounds, floor, observer mode and absence of skulls are checked. `tests/check_wither_idle_flight.py` checks the captured report and requires exactly the two expected baseline failures.

The identical final fixture passed 74/74 checks on vanilla and patched Pumpkin. Baseline passed 72/74, with only the two active-flight assertions failing. Patched horizontal excursions were 2.40 and 4.89 blocks; the test establishes resumed wandering, not identical routes or speeds. Each server ran 1,456 verified controlled ticks including cleanup. Fixture and command hashes matched; all scratch servers stopped, cleanup passed, and server/client logs contained no ERROR, panic or uncaught-thread exception lines. Detailed local evidence is in `artifacts/jaron-wither58-validation.json`.

The existing eight-tick visible-target pursuit fixture also passed 26/26 checks on each of vanilla and patched Pumpkin across two repetitions, including main-head target metadata and pursuit. This control begins with the target present; it does not establish preemption of an already-running stroll.

Workspace formatting, all 444 core Rust library tests, core all-target/all-feature Clippy and the debug server build passed under the shared Cargo lock with one job, disabled debug info/incremental compilation, and 5 GiB / no-swap / two-CPU limits. The existing `proc-macro-error2` future-compatibility notice remains. The initial validation attempt stopped at an import-formatting failure before compilation; it was corrected before these successful checks. An initial arena roof exceeded the original height bound; final vanilla, baseline and patched evidence all use the corrected roof at Y=96.

Patched source SHA-256: `dbb0d5d601f75e81186ffa8ab0279d296f80dedcd51a12579ae6e00915836c12`. Copied debug binary SHA-256: `7bc0e423bea692cc14b7bdd2b2c51906e71bb641ec1e41a5518e439cda23c5bc`. Source/copy/fixture/stimulus hashes, process stops, cleanup and clean server/client logs were checked. Local provenance and pursuit details are in `artifacts/jaron-wither58-source-provenance.json` and `artifacts/jaron-wither58-pursuit-validation.json`.

## Limits and human observation

Random wandering is checked by movement presence, not an identical random route or distribution. This fixture does not establish exact flight speed, vertical physics, obstacle routing, goal preemption after an existing route, gravity restoration, Bedrock behavior or full-fight parity. The existing flying navigation and movement-controller integration have separate limitations; PR 4092 remains relevant to those. Regression coverage is an executable world fixture, not a new isolated Rust unit test.

For a human check, use a disposable enclosed arena with no eligible targets and observe the Wither wander. Compare a NoAI Wither and a Wither during its spawn countdown, then introduce an eligible target and observe pursuit. Record the movement and transitions with a real client before any upstream submission. No rendered-client capture is claimed.
