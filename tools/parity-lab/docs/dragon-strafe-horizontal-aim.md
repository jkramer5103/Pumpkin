# Dragon strafe horizontal aim

Strafing dragons use horizontal alignment to decide when to attack. Pumpkin
previously normalized the full three-dimensional target displacement, so a player
20 blocks below a dragon and 30 blocks ahead prevented an otherwise aligned shot.
The phase now projects the displacement onto the horizontal plane before the
existing normalization and angle check. Range remains a three-dimensional check;
line of sight, charge accumulation and attack side effects retain their ordering.

Vanilla reference: Minecraft Java 26.3 `DragonStrafePlayerPhase.doServerTick`.
The target's X/Z displacement forms `aim`, with Y explicitly zero. That direction
is normalized and compared with the horizontal facing direction after sight and
range checks. The caller ticks the phase before steering, so the arena resets yaw
and velocity before each controlled tick. Only this phase uses the changed local
variable; no shared math or entity code changes.

Initial isolated reproduction: a naturally acquired survival target stands at
(8,80,0), and the dragon is reset to (8,80,30) or (8,100,30), yaw zero. Vanilla
attacks on tick five at both heights. Baseline Pumpkin attacks on tick five at
equal height and stays in strafing through six ticks at the elevated position.
Player presence, health, NoAI, positions/velocity, phase acquisition, clear wall,
controlled tick advances and cleanup are retained in the raw report.

Focused regression: `fixtures/dragon-strafe-horizontal-aim/cases.json` and
`tests/check_dragon_strafe_horizontal_aim.py`. Two trials cover equal height,
20-block elevation, 40-block elevation and an off-axis facing control. Each uses
five controlled ticks after an out-of-range charge drain. Private target state is
not injected: the existing bounded circling acquisition selects a real survival
player before the controlled phase begins. Random acquisition ticks are excluded
from controlled-stimulus comparisons.

Rust validation passed: 490 `pumpkin-core` library tests, workspace formatting,
core all-target/all-feature Clippy and the debug server build. All Cargo
operations used the shared build lock, one job, disabled debug information and
incremental compilation, and the 5 GiB/zero-swap/200% CPU scope limits. The existing
`proc-macro-error2` future-compatibility notice remains.

The identical final arena passed 8/8 cases on vanilla and patched Pumpkin.
Baseline passed 4/8 cases, failing exactly the two elevated cases in each trial:

| Case | Vanilla / patched first attack | Baseline first attack |
| --- | --- | --- |
| Equal height, yaw 0 | Tick 5 | Tick 5 |
| Dragon 20 blocks above player, yaw 0 | Tick 5 | No attack in 5 ticks |
| Dragon 40 blocks above player, yaw 0 | Tick 5 | No attack in 5 ticks |
| Dragon 20 blocks above player, yaw 30 | No attack in 5 ticks | No attack in 5 ticks |

All phase-acquisition, position/yaw/velocity resets, player health and presence,
NoAI, clear-wall, exact one-tick advance and cleanup checks passed. Each target
received 40 controlled attack ticks. Controlled-stimulus hashes match across all
three targets; fixture, source and copied-binary hashes match the validation
records. All scratch processes stopped, and server/client logs contained no
ERROR/panic lines. Evidence is headless protocol 777 and server state only.

Retained local evidence: `artifacts/christine-dragon61-rust-validation.json`,
`artifacts/christine-dragon61-live-validation.json`, and the raw final report at
`artifacts/christine-dragon61-strafe-live-20261020T174430.440059Z/report.json`.
The earlier two-case discovery report remains at
`artifacts/christine-dragon61-strafe-live-20261020T173228.420524Z/report.json`.
No new mocked Rust unit test is added for this world-dependent phase behavior;
the focused world fixture and checker supply the regression coverage.

The [tracker](https://pumpkinmc.org/tracker/) and
[mob-AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) remain
leads. Prior contact gate fixes are complete; multipart foundations remain covered
by open PRs. Fresh public diffs for #3407/#3661/#3835/#4080/#4092 do not alter this
strafe angle gate. Authenticated GitHub searches for open dragon/strafe/strafing
PRs were refreshed after authentication was repaired; no matching correction was
found. No upstream code was copied.

This change validates attack eligibility, not a full boss fight. Pumpkin's current
attack still creates a cloud directly instead of launching a dragon fireball.
Existing strafe routing, precise numeric angle boundaries, projectiles and other
boss behavior remain outside this correction. Headless protocol/server evidence
is not rendered-client proof. A human play check should observe an acquired
strafe target below a horizontally aligned dragon in an isolated arena and
confirm firing without forcing the dragon to descend to the player's height.
