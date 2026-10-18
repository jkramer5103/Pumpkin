# Wither skulls without a living shooter

A skull with no resolved living shooter should deal 5 HP of magic impact damage. Pumpkin always used 8 HP of Wither skull damage, so ownerless impacts killed targets that vanilla leaves alive and incorrectly allowed armor to reduce the hit.

The Rust correction resolves the owner before impact and uses the vanilla living-owner branch: a living shooter retains 8 HP of skull damage and the existing direct-kill heal; otherwise the hit uses `DamageType::MAGIC` and 5 HP. The existing damage dispatch, heal path and explosion still run. This task does not change direct-hit attribution, effect acceptance or projectile flight.

## Reference and overlap

Reference: official Minecraft Java 26.3 `WitherSkull.onHitEntity`, including `getOwner() instanceof LivingEntity`, the magic fallback and the subsequent explosion. Decompiled reference files and hashes remain outside Git.

Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` was fetched and is already an ancestor of this branch. Read-only upstream master `998c3f872c39bb68167c6f2a47799730a23aa751` retains the unconditional damage call. Previous spawn-window goal corrections are complete; [the tracker](https://pumpkinmc.org/tracker/) and [Mob AI #3468](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) were inspected as leads.

Open [#3835](https://github.com/Pumpkin-MC/Pumpkin/pull/3835), head `3640e87c42efc5d582ae10d797c891a327067760`, adds shooter attribution, accepted-hit effects and shared flight fixes but still always applies 8 HP of skull damage. This patch addresses the separate missing magic fallback. An initial explosion-scaling lead was skipped because open [#3694](https://github.com/Pumpkin-MC/Pumpkin/pull/3694) contains that exact correction. [#3905](https://github.com/Pumpkin-MC/Pumpkin/pull/3905) concerns wind-charge effects and knockback. No upstream write actions were taken.

## Regression and validation

The committed `wither-skull-ownerless-damage.json` fixture uses an isolated, forced-loaded arena and a connected headless protocol-777 client. Ordinary and dangerous skulls strike a golem 2.5 blocks above its feet. Both servers' explosion centers are thus outside the two-block splash damage radius, isolating impact damage despite existing projectile collision-order differences. Armor 0, armor 20 and a 6 HP golem cover damage amount, magic armor bypass and survival. Health is checked after impact and again 25 ticks later. Death-removal barriers prevent selectors from matching prior targets.

Two identical fixture trials passed **54/54** assertions on vanilla and **38/54** on baseline Pumpkin `ee6fbd95a342ec6f4eaa0954ca9c141f74601159`. Exactly sixteen health assertions fail before the correction: ordinary/dangerous golems finish on 92 HP, the armored golem on 97.12 HP, and the 6 HP golem dies. Vanilla produces 95, 95, 95 and 1 HP respectively. A supplemental two-trial probe redirects a naturally fired skull with its living shooter retained, checking the unchanged 8 HP impact and shooter health. Identical measured command hashes distinguish random shot-capture delay from the measured stimulus.

The natural-shot controls passed **24/24** assertions on both reference servers. Combined reference results are vanilla **78/78**, baseline **62/78**. Fixture and measured-command hashes match. All four reference scratch processes stopped; both Pumpkin logs contain completed save/stop markers and no error/panic was found in the server/client logs. Vanilla full-save completion is not verified within the harness shutdown grace.

All **443 core Rust library tests**, workspace formatting, core all-targets/all-features Clippy and a full debug server build passed under the shared Cargo lock and the required one-job, no-debug-info, no-incremental, 5-GiB/no-swap/200%-CPU limits. The copied binary and source-file hashes were verified. The final upstream search retained the same open PR heads and found no duplicate magic-fallback fix.

Patched Pumpkin passed **78/78** assertions, matching vanilla; baseline passed **62/78**. Both patched fixture trials produced exactly 95, 95, 95 and 1 HP, including the delayed health checks. Both naturally owned-shot controls retained 8 HP impact damage. All measured command/fixture hashes match the references, and the patched reports identify the copied binary by SHA-256. All six comparison scratch processes stopped; all four Pumpkin logs contain completed save/stop markers. No error/panic was found in the final server/client logs. Vanilla full-save completion remains unverified within the existing harness grace period. Raw reports, hashes, Rust command results and final overlap responses remain in local task-37 artifacts outside Git.

## Limits

These are bounded direct-impact checks, not a rendered-client recording or a full boss fight. The live fixture exercises absent owners; removed, unloaded and nonliving resolved owners are not independently reproduced. Arbitrary living shooter types, plugin listeners, shared projectile movement, direct-hit context, accepted-hit effect gating and skull splash scaling remain outside this patch. Existing Java native/Unsafe, offline-mode, debug-build and proc-macro future-compatibility warnings are not gameplay evidence.
