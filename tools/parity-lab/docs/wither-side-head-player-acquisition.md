# Wither side-head player acquisition

Pumpkin's side-head search called `World::get_entities_at_box`, which explicitly
contains only nonplayers. Vanilla's `WitherBoss.customServerAiStep` searches
`LivingEntity.class`, including players. A survival player could stand eight
blocks from an otherwise idle Wither without either side head targeting them.

Use the existing `World::get_all_at_box` query for this boss-specific search.
The existing living-entity, attackability, Wither-friend, distance, and visibility
filters still decide eligibility. No world query contract or shared AI code is
changed. Creative and spectator players remain ineligible.

Regression fixtures are `wither-side-head-player-survival.json`,
`wither-side-head-player-creative.json`, and
`wither-side-head-player-spectator.json`. A connected protocol 777 client occupies
a bounded bedrock arena. Each case has a fresh Wither and the sole player eight
blocks away. Resistance protects the player, and a location guard verifies the
player remains in place. Easy difficulty excludes idle skull fire. The harness
resets the boss position and motion every five ticks, advances exactly 65 ticks,
and records
both side-head target IDs and skull spawn packets. Survival must acquire the
actual player entity ID from the login packet with both heads and fire skulls;
creative and spectator must acquire neither head and fire no skulls.

Validation on 2026-10-16:

- `cargo fmt --all -- --check` passed.
- `cargo test --locked -p pumpkin-core --lib`: 443 tests passed.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features` passed.
- `cargo build --locked -p pumpkin` passed.
- All Cargo operations used the shared lock, one job, disabled debug info and
  incremental compilation, and the prescribed memory/CPU limits.
- Two repetitions of the three identical fixtures: vanilla and patched Pumpkin
  each passed 42/42 checks; baseline passed 38/42. Only survival acquisition and
  skull fire failed on baseline, twice each. Both side heads acquired the actual
  player ID from the login packet in vanilla and patched survival cases.
- All cases advanced exactly 65 fixture ticks plus 25 cleanup ticks, verified
  from game-time barriers. Fixture and command hashes matched across targets.
  Boss health stayed 300 and player health stayed 20; location guards passed.
- All three scratch servers stopped without ERROR or panic lines.

Local evidence is `artifacts/jaron-wither16-verify.json` and
`artifacts/jaron-wither16-validation.json`, with the raw reports referenced in
the latter. The tested Wither source SHA-256 is
`421aca4ecc71b57981585faebec2436fe0f66e8c37a8bb75894dabbc847697b9`;
the patched binary SHA-256 is
`cd62c637dff45069716e6e8c787b557b36634fda4c2c4ef561b3b329e9a47b51`.

This patch covers only side-head player acquisition. The main-head predicated
active-target goal also searches a nonplayer collection; that is a separate
observed candidate. Main-head targeting/timing, fight balance, projectile
collision, damage, exact skull counts/cooldowns, player transitions, stealth
range scaling, and visuals are not validated here. A headless client provides
protocol observations only.

Upstream overlap was checked read-only on 2026-10-16. The Wither PR search and
PRs 4092, 3425, 3984, 3795 and 4086 contain no equivalent side-head query change.
PR 3865 addresses death drops and PR 3835 addresses projectile behavior.
Fork master 65bca3f is already an ancestor of the campaign branch; upstream master
remains 5b53f06. The other lane's living/dragon source reservations are preserved.
