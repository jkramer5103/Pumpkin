# Wither skull launch origin

Fix: `538338809b0a2f0dfdaf70fe57850bce14323592`.

Naturally fired skulls used the central eye position for all three heads. The Wither computes each firing head's coordinates, but `WitherSkullEntity::new_shot` calls `ThrownItemEntity::new`, which overwrites the position with the shooter's eye minus 0.1. Restore `head_pos` with `Entity::set_pos` immediately before spawning. This keeps the correction in the Wither and updates position/bounds consistently without changing other thrown-item callers or the existing spawn event.

Vanilla 26.3 `WitherBoss.performRangedAttack` constructs its projectile, assigns the owner/dangerous flag, and then calls `setPos(hx,hy,hz)` before `addFreshEntity`. For a default-size Wither at (4.5,80,8.5), the main launch is (4.5,83,8.5); side launches have Y 82.2 and horizontal radius 1.3. Baseline Pumpkin emits every skull at (4.5,82.8750001431,8.5).

## Source and overlap

Campaign baseline `665a191`, upstream `998c3f8`, fork master `65bca3f`. Fork master is already an ancestor; existing campaign corrections remain. The affected launch code retains the upstream constructor behavior. Read-only review of [PR3835](https://github.com/Pumpkin-MC/Pumpkin/pull/3835) at `3640e87`, [PR4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092) and [PR3865](https://github.com/Pumpkin-MC/Pumpkin/pull/3865) found no Wither launch reanchoring. These respectively change shared projectiles/direct impacts, AI foundations and drops. No upstream implementation was copied.

## Bounded validation

Passed under the shared Cargo lock, one build job, disabled debug info/incremental compilation, and systemd limits of 5 GiB memory, no swap and 200% CPU:

- Workspace formatting check.
- `cargo test --locked -p pumpkin-core --lib`: 443 passed.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`.
- `cargo build --locked -p pumpkin`.

The exact patched debug binary SHA-256 is `1257321d3aa198aa68c24a95b44d1dd77858696ef82b40e0b03f62efe04922de`; its Wither source hash matches the source commit.

Two trials at each initial yaw 0/90 used a connected protocol 777 headless client and 45 individually verified ticks. Before each tick the Wither's position and motion were reset; skull spawn packets were compared with that known pre-travel position, since the boss moves after firing. Each skull was removed immediately after capture to isolate spawning. Vanilla and patched Pumpkin each pass 46/46 checks. Baseline passes 34/46, failing exactly twelve launch positions: eight side shots and four main shots.

The permanent `wither-skull-head-origin.json` regression uses 20 one-tick windows, observes a real skull on the side-head ring with a scoreboard, and removes skulls before they reach the sheep. Two trials per target pass 18/18 checks on vanilla and patched Pumpkin; baseline passes 16/18, failing only the launch-ring assertion in each trial. The committed fixture is exactly the tested file.

Combined results are vanilla/patched **64/64**, baseline **50/64**. Gameplay command hashes match across targets for each probe; fixture hashes, binary/source provenance, client presence, health controls and error-free server/client logs were checked. All six server processes stopped. Four Pumpkin logs confirm completed shutdown; both vanilla logs show world saving and RCON listener shutdown without a full shutdown-completion marker within the existing harness grace.

Runtime evidence stays outside Git: `artifacts/jaron-wither25-{validation,verify,source-provenance,overlap}.json`, the `jaron-wither25-launch-{vanilla,baseline,fixed}-*` reports, and task25 fixture reports. No jars, decompiled source, worlds or credentials are committed.

## Limits and excluded exploration

Headless packet/server-state evidence does not prove rendered appearance or a complete boss fight. Only default scale was tested; body yaw versus entity yaw and scaled head coordinates remain independent leads. Skull flight acceleration/inertia, direct-impact immunity/healing/effect acceptance (PR3835), death/star behavior (PR3865), and broader combat/plugin interactions remain outside this correction.

An exploratory 25-tick probe compared coordinates against the boss after travel and omitted the main shot; its failed classifications are excluded. The probe's baseline `kind` field reflects its broken radial position; final assertions distinguish main/side shot windows by tick and check both height and radius.

The first patched 45-tick unrestricted-flight run matched launch positions but failed the sheep full-health control after projectiles could reach it. That run remains excluded from clean validation. Final comparisons remove skulls after capture on all three targets; they do not establish damage, resistance or flight parity. The initial Rust attempt stopped before Cargo because free space fell below 6 GiB. Only historical lane-owned task22/23 binaries were losslessly archived with decompressed SHA verification before the successful restart. The existing `proc-macro-error2` future-compatibility warning remains.
