# Wither minecart pickup immunity

A moving empty minecart overlapping a Wither must leave the boss unmounted.
Vanilla rejects natural mounting at full health, half health, during spawn
invulnerability and with NoAI. Cow and zombie pickup and an explicit forced
`/ride` are positive controls.

Vanilla 26.3 `OldMinecartBehavior.pushAndPickupEntities` and
`NewMinecartBehavior.pickupEntities` call the passenger's `startRiding`.
`Entity.startRiding` checks `canRide` unless forced; `WitherBoss.canRide`
returns false. Pumpkin's minecart path added passengers directly after checking
only the boarding cooldown, so the Wither override had no equivalent.

The correction checks normal riding eligibility before minecart pickup and
provides the Wither veto through the mob trait. Existing low-level passenger
insertion remains available to forced `/ride` and NBT loading; mount and vehicle
entry plugin events retain their existing cancellation point.

The retained `lab/examples/wither-minecart-pickup-immunity.json` is the focused
regression: moving cart collision, four boss states, two ordinary mobs, forced
mount, and exact one-tick observations. This requires a live world, so the regression uses the existing comparison
harness. Commands read passenger state, and the connected headless client
independently records subject/cart spawn and passenger packets. Each stepped
tick settles for 200 ms while frozen before state is read.

Scope: no general vehicle physics, speed threshold, boat pickup, client
rendering, reload or complete Wither fight claims. No live plugin listener was
attached. For a human play test, place a moving cart against a Wither in a
contained arena and observe that it stays free; compare ordinary-mob pickup.
Capture the collision and rejected mounting with a real client if preparing an
upstream submission. No upstream PR was opened.

Overlap: checked current fork/upstream master and open PRs. PR3794 changes the
minecart implementation but still inserts passengers without a Wither veto;
PR4092 covers the separate NoGravity effective-gravity guard, which is deferred.

Rust validation passed: 444 `pumpkin-core` library tests, workspace formatting,
`pumpkin-core` all-targets/all-features Clippy, and a debug `pumpkin` build. All
Cargo operations used the shared build lock, one job, disabled debug info and
incremental compilation, and the prescribed memory/CPU limits. The existing
`proc-macro-error2` future-compatibility warning remains.

Final live comparison used the same fixture and command sequence for two trials
per target, with 389 controlled ticks each:

| Target | Checks passed | Failures |
| --- | ---: | --- |
| Vanilla 26.3 | 126/126 | None |
| Baseline `3391fffed` | 110/126 | Eight Wither mounts, each confirmed by state and passenger packet |
| Patched Pumpkin | 126/126 | None |

The baseline incorrectly picked up all four Wither states in both trials.
Ordinary cow/zombie pickup and forced Wither mounting passed on every target.
Fixture, command-sequence, patched-source and copied-binary hashes were checked.
All three scratch servers stopped and boss cleanup passed. Both Pumpkin saves
completed. Final server and client logs contained no ERROR, panic or uncaught
thread-exception lines. Vanilla's complete-save marker was not observed within
the shutdown grace period.

An earlier observation read cow passenger state before its tick finished even
though its later passenger packet confirmed mounting. The final comparison
settled stepped ticks while frozen before reading state. Earlier exploratory
samples are excluded from the table.
