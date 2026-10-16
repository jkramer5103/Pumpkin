# Wither autonomous main-head targeting

An unprovoked Wither never set its main-head target in Pumpkin. The side heads
could still attack, hiding the missing target goal. Withers now select nearby
eligible living entities without needing retaliation.

Register the existing class-agnostic `ActiveTargetGoal` at priority 2, after
revenge at priority 1. Its search interval is zero, it does not require a
navigable path, and its selector excludes the generated `WITHER_FRIENDS` tag.
The existing combat predicate supplies living, attackability, distance and sight
checks. Sight is required at acquisition; the false sight flag controls continued
tracking, matching vanilla. No shared targeting or combat files changed.

Reference: official Minecraft 26.3 `WitherBoss.registerGoals`, its living selector,
`NearestAttackableTargetGoal` constructors/search/start, `TargetGoal` continuation,
and `LivingEntity.attackable`. Decompiled material remains outside the repository.
The tracker and issue [3468](https://github.com/Pumpkin-MC/Pumpkin/issues/3468)
were leads; source inspection and runtime comparison confirmed the missing goal.

Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` was fetched and is already
an ancestor. Upstream master `5b53f064af8708ba33fcaa533b81ca29a53a3310` has the same
missing registration. Read-only open-PR searches on 2026-10-16 found no overlapping
fix: 3865 changes death drops, 4038 effect immunity, 3835 projectile behavior,
and 3793 velocity/tick plumbing. No upstream publication was made.

## Reproduction and regression coverage

Baseline binary: campaign commit `428701f0a89bc8d9adffba477708ed970ee694b8`.
The four `wither-main-head-*.json` fixtures use fresh isolated arenas with a
connected protocol 777 client, a creative observer, an unharmed active Wither,
Easy difficulty and stationary target mobs. Each advances eight verified ticks.
Main-head `DATA_TARGET_A` is metadata 16 in this protocol; inspect it separately
from side-head attacks.

| Case | Baseline main head | Vanilla and patched main head |
| --- | --- | --- |
| Visible sheep, eight blocks east | Zero | Sheep |
| Closer zombie plus visible sheep | Zero | Sheep |
| Only zombie | Zero | Zero |
| Sheep behind bedrock | Zero | Zero |

The closer zombie is four blocks north of the Wither, outside the skull path to
the sheep. Fixtures check boss health/invulnerability, observer mode, target
presence, wall state where applicable and pursuit of eligible targets. Negative
cases allow idle wandering, with an arena guard and a zero main-target packet
assertion. A stationary-boss assertion is inappropriate because vanilla can
wander even without a target.

## Validation

The workspace formatting check, all 443 core library Rust tests, core
all-targets/all-features clippy and a full `pumpkin` binary build passed. Cargo
used the shared build lock, one job, disabled debug information/incremental
compilation and the required 5 GiB/CPU caps. The existing `proc-macro-error2`
future-incompatibility notice remains.

Two repetitions of all four final fixtures passed 100/100 checks on vanilla
and 100/100 on patched Pumpkin. Baseline passed 92/100, failing only main-head
acquisition and pursuit in both repetitions of the two eligible-target cases.
Fixture hashes matched across all three binaries. Every case advanced exactly
eight ticks, and all three scratch servers stopped without ERROR/panic lines.
Main-target values named the sheep in both positive cases and stayed zero in
both negative cases. Test drivers, raw packets and logs remain outside the repo.

## Limits and next lead

An earlier fixture placed the closer zombie directly in the skull path. In both
patched trials, boss health fell to 298.03992 after target acquisition while
vanilla retained 300. The final fixtures avoid that interference; the earlier
combat discrepancy remains a separate investigation, with no source cause
claimed here. Initial parser-format and idle-stationarity failures are preserved
in exploratory reports and excluded from the final validation counts.

This patch restores autonomous selection using existing targeting primitives.
Attack cooldowns, ranged-goal/navigation parity, damage immunities,
invisibility/sneaking distance scaling, side-head eligibility changes,
retaliation preemption and complete boss fights remain unverified. Evidence uses
a headless protocol client; no human visual proof is claimed.
