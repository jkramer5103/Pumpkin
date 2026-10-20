# Wither main-head retargeting

When retaliation selects a new attacker, the running ranged attack goal kept its
old target. Wither target metadata changed to the attacker, but the next central
skull still flew toward the original victim. Vanilla refreshes the ranged goal's
cached target from `canUse()` during `canContinueToUse()`.

The Rust continuation check now calls `can_start()` first. This updates the cached
target without restarting the goal or resetting the attack cooldown. Its fallback
also follows vanilla: retain a living cached target while navigation is unfinished.
The existing stop behavior is unchanged.

Reference: locally decompiled official Java 26.3 `RangedAttackGoal.canUse`,
`canContinueToUse`, `tick`, `WitherBoss.registerGoals`, and
`HurtByTargetGoal.start`. Fork master `65bca3f7f36a` is already an ancestor of the
campaign branch; upstream master was `fb7c8e223a38` at investigation time.
[Mob AI tracker](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[parity tracker](https://pumpkinmc.org/tracker/) were checked as leads.

Open [PR 4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092) changes this goal's
navigation lock access but leaves its continuation target cache unchanged.
[PR 4107](https://github.com/Pumpkin-MC/Pumpkin/pull/4107) changes target selection
and leaves the ranged goal unchanged. Current Wither and ranged/retarget PR searches
found no matching correction. Cobweb slowdown immunity was inspected and is already
implemented; no change was made there. Provider-rejected work remains excluded.

## Regression

`lab/examples/wither-ranged-retarget.json` contains a sealed arena within
x/z 0..31 and y79..96. A powered Wither acquires a sheep, then takes one point of
command-attributed damage from a cow on the opposite side. Both targets have
1000 health and remain alive. All measured entities and the observer occupy
chunk0. NoAI targets, NoGravity and zero Wither movement and flying speeds isolate
targeting from movement. Each direction is exercised twice;
an undamaged control retains its sheep target. Each case advances exactly 68 ticks,
including cleanup before setup. Final cleanup advances another 26 ticks.

A headless Java protocol observer records target metadata and skull spawn packets.
`tests/check_wither_ranged_retarget.py` requires initial sheep targeting, final cow
targeting after damage, exactly one central skull at y83 and its horizontal velocity
toward the current target. The side-head launch height y82.2 separates their shots.
Live command checks require both victims and the boss alive, initialized health,
active AI, arena containment and a connected creative observer.

Initial exploration with invulnerable victims prevented target acquisition. A
second exploration allowed the sheep to die. Those attempts are excluded. Explicit
max-health/health controls preserve both victims. The first final comparison also
exposed two invalid test controls: vanilla omits default `NoAI:0b` from NBT, and
the headless observer had not tracked victims across the chunk boundary. Active AI
is now checked with `unless NoAI:1b`; all measured entities occupy chunk0. Fresh
identical comparisons supersede those reports. Corrected exploratory runs
reproduced opposite central-shot directions in vanilla and baseline Pumpkin
with both victims alive.

## Validation

Under the shared Cargo lock and prescribed resource limits, workspace formatting,
all 444 core library Rust tests, core all-target/all-feature Clippy and a debug
server build passed. The existing `proc-macro-error2` future-compatibility notice
remains. The first attempt stopped on formatting before compilation; its logs are
retained separately. The corrected source is the source used for the final build.

The identical final fixture passed 75/75 checks on vanilla and patched Pumpkin.
Baseline Pumpkin passed 71/75, failing exactly the four central-skull direction
checks after retaliation. Both targets survived every case; target metadata
changed to the cow on all three targets. The undamaged control kept shooting
at the sheep. Each target ran 366 controlled ticks, with a central skull fired
within the same 43-tick observation window, guarding against a cooldown reset.

Fixture and command stimulus hashes match. The source hash matches the Rust
verification record; the copied binary hash matches the patched runtime report.
Cleanup succeeded, scratch servers stopped, and server/client logs contain no
errors. Evidence is retained locally in `artifacts/jaron-wither59-validation.json`,
`artifacts/jaron-wither59-verify.json` and the reports they reference. The final
upstream search still found no overlapping target-cache correction.

## Limits

This is a command-controlled retaliation and headless packet regression, not a
natural player combat, rendered-client or whole-fight test. Projectile flight,
knockback and exact movement are not assessed; their existing differences are
outside this patch. The navigation fallback follows vanilla source but has no
separate live route-loss case here. The shared goal also serves witches, snow
golems, llamas and trader llamas; their target caches receive the same correction,
but those species have not been exercised live by this fixture. No new isolated
Rust unit test is added; coverage is the retained gameplay fixture and checker.
