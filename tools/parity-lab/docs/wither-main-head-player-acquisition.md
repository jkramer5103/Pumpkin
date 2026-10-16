# Wither main-head player acquisition

Source/test commit: e549f92cb58bd643df8ff1b949a65e7ddc4a4493.

The Wither main-head target goal searched only Pumpkin's nonplayer entity
store. With a survival player present its target remained zero; with a nearer
player and farther sheep, it chose the sheep. Vanilla 26.3 selected the player.
The side-head correction in 924bc884 is separate from this main-head omission.

Vanilla reference: `WitherBoss.registerGoals` registers a
`NearestAttackableTargetGoal<LivingEntity>`, interval zero, with the
`LIVING_ENTITY_SELECTOR`. `NearestAttackableTargetGoal.findTarget` obtains living
entities including players, applies target conditions, and chooses the closest
eligible candidate to `(getX(), getEyeY(), getZ())`.

The class-agnostic `ActiveTargetGoal` now searches both Pumpkin stores with the
existing predicate and condition, then compares their closest eligible results.
Typed target goals and grudge lookup retain their existing paths. The only other
class-agnostic caller is Iron Golem: its monster-category predicate excludes
players, so scanning players cannot select one there. Existing range, sight,
attackability and team filters remain in force.

Fork master65bca3f was already an ancestor of task baseline924bc884; upstream
master5b53f06 was unchanged at final fetch. The
[Mob AI issue3468](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[tracker](https://pumpkinmc.org/tracker/) were leads. Open Wither PRs4038
(skeleton),3865 (death/drop),3835 (projectiles),3793 (touch), and shared
PRs4092,3425,3984,3795,4086 do not implement this correction. Searches were
refreshed before publication.

Validation passed:

- `cargo fmt --all -- --check`;
- `cargo test --locked -p pumpkin-core --lib`: 443 passed;
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`;
- `cargo build --locked -p pumpkin`.

Cargo ran under the shared build lock, one job, disabled debug info/incremental,
and systemd MemoryMax5G/MemorySwapMax0/CPUQuota200%. Existing dependency
`proc-macro-error2` future-incompatibility warnings remain.

The final isolated, engine-locked replay used six fixtures, twice each: sole
survival/creative/spectator player, player nearer than sheep, sheep nearer than
player, and creative player with sheep. Easy difficulty, Resistance V, fixed
initial positions and exactly eight ticks isolate initial acquisition. A logged-in
headless protocol777 client captured actual player/sheep IDs and main-head
metadata16. Vanilla and patched Pumpkin each passed84/84 focused checks, including
all12 target decisions; baseline passed80/84, failing only survival and
player-nearer acquisition in both repetitions. Matching fixture/command hashes,
exact eight-tick barriers plus25 cleanup ticks, player position/mode/health,
Invul0, competing sheep packets, source/binary provenance, clean shutdowns and
absence of ERROR/panic lines in the three final server logs were verified.

Local evidence is retained in `artifacts/jaron-wither17-validation.json` and
`artifacts/jaron-wither17-verify.json` in the deployment workspace; raw reports,
binaries, bot scripts and decompiled Java are not published in this branch.
The JSON fixtures provide command guards; main-head acquisition needs the protocol
metadata observation described in their notes, rather than a command-only pass.

Known limits: in both sheep-nearer repetitions, baseline and patched Pumpkin
report boss health298.01456 versus vanilla300. Health remains a diagnostic;
this acquisition patch does not correct that separate combat discrepancy. An
excluded preliminary65-tick run also hit a pre-existing Resistance amplifier255
arithmetic overflow in `LivingEntity.get_damage_after_magic_absorb`. Final runs
use amplifier4 and do not panic. Skull damage, exact attack timing, pursuit,
mode transitions, equal-distance tie order, stealth scaling and full fights are
not established. No human client visual proof is claimed.

## Dеscription ·

> This description was drafted by an AI agent (Codex, gpt-6.1-sol).

Include connected players in the Wither's autonomous main-head target search.
Compare the nearest eligible player and nonplayer so neither storage category
receives unconditional priority.

## Tеsting ·

443 core Rust tests, formatting, clippy and the binary build passed. Two
repetitions of six headless acquisition fixtures match vanilla:84/84 focused
checks on vanilla/patched,80/84 on baseline. Separate boss-damage discrepancy
remains; this is not complete fight or visual validation.

Human play-test checklist: in an isolated easy-difficulty arena, summon a Wither
near a survival player; expect the main head to acquire the player without being
hit first. Repeat with a sheep closer and farther away, and with a creative or
spectator player; expect the closest eligible living target and exclusion of
creative/spectator players. Capture a recording of main-head tracking and fire.

Capture: <attach screenshot or recording here>

Before an upstream submission a human must read the patch, play-test with a real
client, attach their capture, and open the PR themselves with disclosure intact.
