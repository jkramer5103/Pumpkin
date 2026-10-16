# Wither retained side-head attackability

After acquiring a golem, Pumpkin's Wither kept targeting it with both side heads
when `Invulnerable` became true. The main head released it. Vanilla releases the
side-head targets at their next scheduled update and stops targeted skull fire.

The retained-target branch now uses the existing `Mob::can_attack` check, as
vanilla `WitherBoss.customServerAiStep` does, instead of checking only entity
liveness. That follows `Mob.canAttack` through `LivingEntity.canAttack` and the
victim's `canBeSeenAsEnemy` overrides. The existing distance and sight checks
still apply. Acquisition and retention deliberately use different distance limits
(20 and 30 blocks).

Regression fixtures are `wither-side-head-invulnerable-release.json` and
`wither-side-head-attackable-retention.json`. A connected creative protocol 777
client keeps Pumpkin's arena loaded and records side-head target metadata. Each
fixture acquires the sole golem before its invulnerability is set, allows 20 ticks
for old shots, clears skulls, and samples every tick for 60 ticks. Easy difficulty
excludes idle random skulls. The invulnerable fixture must emit no new skulls;
the attackable control must still emit skulls. Both head IDs must clear only for
the invulnerable victim. Run in fresh isolated scratch worlds with verified tick
advancement and two repetitions per fixture.

Validation on 2026-10-16:

- `cargo fmt --all -- --check` passed.
- `cargo test --locked -p pumpkin-core --lib`: 443 tests passed.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features` passed.
- `cargo build --locked -p pumpkin` passed.
- All Cargo work used the shared build lock, one job, disabled debug info and
  incremental compilation, and the prescribed 5 GiB memory / 200% CPU limits.
- Two repetitions of each identical fixture: vanilla and the patched immutable
  binary passed 36/36 checks each. Baseline passed 32/36; only target release and
  skull suppression failed, twice each. Positive attackable-target controls
  passed on all three servers. Every fixture advanced exactly 85 verified ticks,
  plus 25 cleanup ticks, with matching scenario and command hashes.
- All three scratch servers stopped without ERROR or panic lines. Withers stayed
  at 300 health. Invulnerable golems stayed at 100; attackable golems survived
  and took damage. Damage amounts are not asserted equal by this patch.

Local evidence: `artifacts/jaron-wither15-verify.json` and
`artifacts/jaron-wither15-final-validation.json`. The patched binary SHA-256 is
`89f71e3c4bf2a322f76337f1579e4564458fe7fe356562e8bd0af02b8a9374ca`.
The original reference reports preserve a failed observer guard that incorrectly
required a golem spawn packet. The final evidence checks acquisition directly:
the sole eligible target has the same nonzero ID in main- and side-head metadata.
No stimulus commands changed, and the patched replay uses this corrected guard.

Open upstream Wither PRs were checked read-only on 2026-10-16. PR 3865 covers
nether-star drops, PR 3835 projectile behavior, and PR 3793 tick/velocity behavior;
none changes retained side-head attackability. PR 4038 concerns Wither Skeletons,
not the Wither boss. Fork master 65bca3f is already an ancestor of this branch;
upstream master 5b53f06 still has the liveness-only retained-target check.

This change does not establish full boss-fight or visual parity. Player mode
transitions are not validated by these fixtures: Pumpkin's side-head acquisition
currently omits players, a separate observed lead. Main-head attack timing,
projectile behavior, team rules, and phase behavior remain outside this patch.
