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
