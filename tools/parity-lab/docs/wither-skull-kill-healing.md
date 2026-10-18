# Wither skull direct-kill healing

A successful direct skull hit that kills its victim should heal the living shooter by five health. Pumpkin discarded the damage result and omitted the heal, so a wounded Wither stayed at its previous health after killing a target with a skull.

The patch checks the damage result and the victim's post-hit life state before healing the resolved living owner with positive health through the existing `LivingEntity::heal` path. Health is checked explicitly because dying living entities remain in Pumpkin's world during their death animation. The owner-health guard preserves vanilla `LivingEntity.heal` ignoring dead owners. Healing happens before the explosion, so a splash-only kill cannot trigger it. The existing heal path preserves max-health clamping and the cancellable regain-health plugin event.

## Reference and overlap

Reference: Minecraft Java 26.3, `WitherSkull.onHitEntity`, the `LivingEntity.isAlive` override, direct damage/death and heal call chains. The vanilla direct-hit branch heals the living owner by 5 only after accepted damage leaves the victim dead.

Fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor of this branch; existing campaign changes are retained. Read-only upstream master `998c3f872c39bb68167c6f2a47799730a23aa751` has the same missing branch. The tracker and Mob AI issue [#3468](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) are leads; the Wither spawn-window goal fix is already on this campaign branch and is not repeated.

Open [#3835](https://github.com/Pumpkin-MC/Pumpkin/pull/3835), head `3640e87c42efc5d582ae10d797c891a327067760`, touches skull direct-hit attribution, accepted-hit effect gating and shared projectile flight. Its skull diff does not implement direct-kill healing. This patch is restricted to the missing heal branch; it does not port or claim those other changes. Open #3865 addresses death loot separately; #4105 concerns the mob-drops gamerule. Neither supplies this healing branch. The final open-Wither/open-heal PR search found no duplicate heal fix. API overlap evidence is retained locally, outside Git.

## Regression and validation

The committed `wither-skull-kill-healing.json` scenario captures a naturally fired skull, pauses and wounds its actual shooter, then redirects the skull into a 4-HP sheep. It checks 200 HP before impact and 205 HP afterward, with the victim dead. A real headless protocol client keeps the arena active.

Supplemental two-trial cases test direct lethal hits, surviving hits on a 40-HP iron golem, rejected hits on an invulnerable target and healing clamped from 298 to 300 HP. The shooter is remote and has NoAI, preventing natural regeneration; health is rechecked after another 25 ticks. Capturing the first real shot allows random AI firing times to differ while the measured impact commands remain identical. The death check accepts either zero-health corpses or vanilla's selector exclusion, after positively checking the target's initial existence and health.

Before the patch, vanilla passed **124/124** checks and baseline Pumpkin passed **114/124**, failing exactly ten shooter-health checks. Both trials executed the committed fixture and all four supplemental cases. All **443 core Rust library tests**, workspace formatting, core all-targets/all-features Clippy and a full debug server build passed under the shared Cargo lock and the required one-job, no-debug-info, no-incremental, 5-GiB/no-swap/200%-CPU limits. Patched Pumpkin passed **124/124**, matching vanilla across all ten rows. The identical fixture and measured stimulus hashes, actual owned-shot creation, projectile consumption, death/survival controls, delayed shooter-health checks, connected protocol-777 clients, cleanup and error-free server/client logs were verified. All three final comparison processes stopped; both Pumpkin save/shutdown markers were verified. Vanilla full-save completion was not observed within the existing harness grace period.

Exploratory reports are excluded from this oracle. Sheep cap health at 8 HP; vanilla selectors exclude dying mobs while Pumpkin includes them. Exploratory blast controls also differ: vanilla kills a cow that survives the direct hit and a separate splash-only sheep; baseline Pumpkin leaves them alive. This patch does not correct or claim equivalent blast damage. Raw exploratory evidence is retained locally for an independent source investigation.

## Limits

This is a bounded impact comparison, not a full boss fight or a rendered-client recording. Arbitrary living owners, unloaded or removed owners, plugins, ownerless direct-damage semantics, direct-hit attribution/effects and flight remain outside this task. Plugin event behavior is preserved by using the existing heal method; no plugin listener was exercised. Existing proc-macro-error2 future-compatibility, Java native/Unsafe, offline-mode and debug-build warnings remain. The first build stopped at disk preflight and a resumed launcher referenced a missing script; both failed before Cargo. The corrected serialized run passed all four Rust commands.
