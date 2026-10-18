# Dragon breath damage sampling

A sheep introduced into an active sitting dragon flame at cloud age 21 should
remain at 8 health through ages 22 and 24, take 3 damage at age 25, remain at
5 health through age 44, and take the next 3 damage at age 45. Pumpkin checked
victims every tick, so the first hit happened at age 22 and the next at age 42.

The Rust correction samples victims every five cloud ticks and stores absolute
reapplication deadlines. Radius changes still run every active tick. The focused
Rust regression covers both the default 20-tick delay and a non-aligned 7-tick
delay, which must wait until the following five-tick sample.

Reference: the local Mojang 26.3 decompilation's `AreaEffectCloud.serverTick`
checks `tickCount % 5 == 0`, removes expired victim deadlines, then applies
instant effects at potency 0.5. No Java source or jars are committed.

## Reproduction and validation

The adjacent `dragon-breath-damage-cadence.json` fixture runs two trials with
actual dragon-emitted clouds. It pauses and moves the emitter away, clears
terrain around the flame, introduces one sheep at the cloud center between
samples, and checks health plus exact tick advances and retained victim position.
An exact-protocol headless client keeps each isolated arena ticking.

Before the fix, vanilla passed 33/33 assertions and Pumpkin passed 27/33, with
exactly the three expected health differences per trial. Report:
`artifacts/christine-dragon35-live-20261018T133821.311517Z/report.json` in the lab
workspace. Both scratch servers and protocol clients stopped.

Patched Pumpkin passed 33/33 using the identical fixture and stimulus sequence:
`artifacts/christine-dragon35-live-20261018T173602.042918Z/report.json`.
The transcript comparison excludes repeated read-only game-time polling queries.
All tick-delta and victim-position controls passed (110 controlled ticks per
target). All three scratch processes stopped, both Pumpkin saves completed, and
no server log contains errors or panics. Vanilla's final save completion was not
confirmed within the harness shutdown grace period.

Under the shared Cargo lock and resource limits, these checks passed:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib` (471 tests)
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

The new Rust regression fails with unrestricted per-tick victim sampling
restored, then passes with the patch. The negative control retains absolute
cooldown deadlines; it isolates the missing sampling gate rather than restoring
every line of the old implementation. Final source, copied binary and fixture
hashes match the validation records. The existing `proc-macro-error2` future
compatibility warning remains.

## Scope and overlap

Fork master was fetched and is already an ancestor of this branch. The newer
upstream master retains the same per-tick victim sampling defect; its unrelated
world-format, data and plugin changes were not imported. Open cloud PRs 3663,
3816 and 3819 do not implement this scheduling correction. Dragon hitbox PRs
[3407](https://github.com/Pumpkin-MC/Pumpkin/pull/3407) and
[3661](https://github.com/Pumpkin-MC/Pumpkin/pull/3661) were inspected; PR 3407
already covers the separate crystal-healing candidate, which was deferred.
Read-only query/file evidence is retained in `artifacts/christine-dragon35-upstream.json`
and `artifacts/christine-dragon35-cloud-upstream.json`.

The shared cloud code also serves lingering potions, strafing clouds and generic
cloud entities. They receive the same vanilla sampling schedule; no constructor,
plugin event, effect eligibility, radius, duration or damage amount changed.
The reapplication map has no external readers. No rendered-client capture,
lingering-potion gameplay, complete dragon fight or natural End landing was tested.

The optional cloud `Age` diagnostic reads 45 in vanilla but is unsupported by
Pumpkin's cloud NBT. It is not counted as an assertion; the comparison uses
controlled tick advances, emission and health/position observations. No cloud
NBT compatibility or full-fight claim is made.
