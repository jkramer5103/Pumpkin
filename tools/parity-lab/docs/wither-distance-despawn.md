# Wither distance despawning

Source and regression fixture: 5d87e9bbd01f3f1bdebf33878f6ea95b5aae7e40.

Pumpkin applied ordinary mob despawning to the Wither. Both an active and a
spawning nonpersistent Wither survived with a connected player 127 blocks above
them. Moving the player to 129 blocks removed both on Pumpkin; vanilla 26.3
retained them. A fresh Wither also disappeared on Pumpkin with only a spectator
connected, while vanilla retained it.

Vanilla `WitherBoss.checkDespawn` overrides `Mob.checkDespawn`: it discards the
boss on Peaceful and otherwise resets `noActionTime`. It never runs ordinary
player-distance or random despawning. Pumpkin's `MobEntity.check_despawn` runs
before `mob_tick`. Its existing `Mob.remove_when_far_away` hook covers random
and distance removal, including an empty eligible-player set. The Wither now
returns false there. Its existing `mob_tick` still removes it on Peaceful,
including with NoAI. No shared mob code or other entity type changes.

Fork master 65bca3f was already an ancestor of baseline a24e38f. Upstream master
5b53f06 was unchanged at final fetch. The [tracker](https://pumpkinmc.org/tracker/)
and [Mob AI issue #3468](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) were
leads. Refreshed open PR searches found no equivalent Wither despawn correction.
[PR #3865](https://github.com/Pumpkin-MC/Pumpkin/pull/3865) corrects star drops;
its source patch was inspected and its description explicitly leaves distance
despawning for later. PR #3407 concerns the Ender Dragon. PR #3835 addresses
projectile collisions and direct damage attribution. PR #4038 does include
Wither boss effect immunity in living.rs, so that candidate was excluded.

Validation passed under the shared build lock, one Cargo job, disabled
incremental/debug info and systemd MemoryMax=5G, MemorySwapMax=0, CPUQuota=200%:

- `cargo fmt --all -- --check`;
- `cargo test --locked -p pumpkin-core --lib`: 443 passed;
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`;
- `cargo build --locked -p pumpkin`.

The existing `proc-macro-error2` future-incompatibility warning remains.

Two repetitions of the identical `wither-distance-despawn.json` fixture passed
44/44 focused checks on vanilla and patched Pumpkin. Baseline passed 34/44,
with exactly five expected failures per repetition: both nonpersistent bosses
removed at 129 blocks, still absent after switching to spectator, and a newly
summoned Wither removed with only a spectator connected. Near-distance survival,
ordinary zombie despawning, a persistent Wither, Peaceful removal and cleanup
controls passed. Fixture and stimulus hashes, all seven exact tick barriers per
repetition, headless client survival, clean stops and absence of ERROR/panic
lines in all three console logs were verified. Source and binary hashes match
the tested Rust patch. Initial narrower reference runs are excluded from these
final counts.

The isolated arena uses forceloaded chunks, bedrock, NoAI/NoGravity, fixed X/Z,
vertical distances 127/129 and two-tick observation barriers. Each repetition
advances ten fixture ticks plus two 25-tick cleanup barriers. This is actual
server-state evidence with a connected protocol 777 headless client, not human
visual or complete boss-fight proof. Spawn timers, skulls, health, random-despawn
cadence, chunk unload/reload and actual player disconnects are not separately
validated. Peaceful star drops remain a separate defect covered by PR #3865.

Local evidence: `artifacts/jaron-wither18-validation.json` and
`artifacts/jaron-wither18-verify.json` in the deployment workspace. Raw reports,
worlds, binaries, bot scripts and decompiled Java are not published.

## Dеscription ·

> This description was drafted by an AI agent (Codex, gpt-6.1-sol).

Prevent Withers from running ordinary mob distance despawning. The boss survives
players moving more than 128 blocks away and spectator-only presence while still
being removed on Peaceful.

## Tеsting ·

443 core Rust tests, formatting, clippy and the full server build passed. Two
repetitions of the isolated headless fixture match vanilla: 44/44 checks each,
versus baseline 34/44 with only the expected Wither survival failures. Exact tick
advances, matching fixtures/commands, binary provenance and clean stops passed.
No real-client visual or complete boss-fight proof is claimed.

Human play test: summon a nonpersistent Wither in a forceloaded arena, move beyond
128 blocks and return; expect the same boss to remain. Repeat during its spawn
phase. Switch to Peaceful and expect it to disappear. Record the outward trip,
return to the same boss and Peaceful removal with a real client before opening
an upstream PR yourself, retaining the disclosure above.

Capture: <attach screenshot or recording here>
