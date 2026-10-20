# Dragon strafing visibility

A strafing dragon must see its target before charging an attack. Pumpkin previously
advanced the charge through solid cover, spawning its current attack effect and
returning to circling on tick five. The phase now requires the existing entity
line-of-sight raycast as well as the existing range test. Loss of sight uses the
existing positive-charge decrement, so brief cover also delays the next attack.

Vanilla reference: Minecraft Java 26.3 `DragonStrafePlayerPhase.doServerTick`,
following `attackTarget`, distance, `hasLineOfSight`, charge increment/decrement,
attack and return-to-holding-pattern branches. The call is the direct entity
raycast, as in vanilla, without using a sensing cache. Navigation and target
selection still execute before the visibility gate.

The initial isolated comparison used two trials with a naturally selected survival
player target, a fixed facing direction and position, cleared velocity, and six
controlled attack ticks. Vanilla stayed in phase 1 behind bedrock; prepatch Pumpkin
returned to phase 0 on tick five in both trials. With no wall, both returned to
phase 0 on tick five. All 22 non-defect controls passed on the baseline.

Focused world regression: `fixtures/dragon-strafe-visibility/cases.json` and
`tests/check_dragon_strafe_visibility.py`. Two trials cover continuous cover, a
clear view, regaining sight after six covered ticks, and interruption of a partial
charge by two covered ticks. The report checker checks attack timing, live
player presence, phase, wall, exact reset positions/velocity, health, NoAI, one-tick
advances and cleanup. It compares the controlled attack stimulus across targets;
random target-acquisition ticks are intentionally excluded from stimulus hashes.
The acquisition stage is bounded at 16 dragons and 24 ticks and uses circling's
normal target selection, without injecting private AI state.

Final validation: 490 `pumpkin-core` library tests passed, along with workspace
formatting, core all-target/all-feature Clippy, and the debug `pumpkin` server
build. Every Cargo operation used the shared build lock, one job, no debug info
or incremental compilation, and the 5 GiB/zero-swap/200% CPU scope limits.

The same fixture ran on vanilla, baseline and patched Pumpkin, with 64 controlled
attack ticks per target. Vanilla and patched Pumpkin passed 8/8 cases; baseline
passed 2/8, failing exactly the two trials of each cover-dependent case:

| Case | Vanilla / patched first attack | Baseline first attack |
| --- | --- | --- |
| Covered for six ticks | No attack | Tick 5 |
| Clear view | Tick 5 | Tick 5 |
| Six covered ticks, then clear | Tick 11 | Tick 5 |
| Two clear, two covered, then clear | Tick 9 | Tick 5 |

Position/velocity resets, wall state, health, NoAI, phase, tick advances, player
presence and cleanup checks passed on all targets. Fixture/controlled-stimulus,
source and copied-binary hashes were checked. All scratch processes stopped;
server/client logs contained no ERROR/panic lines. Existing
`proc-macro-error2` future-compatibility notice remains.

Local retained evidence: `artifacts/christine-dragon60-rust-validation.json`,
`artifacts/christine-dragon60-live-validation.json` and the raw report at
`artifacts/christine-dragon60-strafe-live-20261020T172320.715535Z/report.json`.
Vanilla omits false `NoAI`; the checker accepts that absence or an explicit zero.
The interrupted yaw probe produced no comparison and is excluded. The initial
strafe discovery used the smaller covered/clear matrix; final results above use
the unchanged four-case fixture on all three targets.

Only phase-local charging/attack eligibility changes. Pumpkin's current strafe
attack effect remains a cloud spawned at the target rather than a traveling
vanilla dragon fireball. Projectile creation/flight, existing aim/path differences,
precise collision hitboxes, natural flight trajectories, and a whole boss fight
remain outside this correction. Headless protocol-client and server state checks
are not rendered-client proof. No new mocked Rust unit test is added for this
world/raycast behavior; the focused world fixture is the regression coverage.

The [mob-AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[parity tracker](https://pumpkinmc.org/tracker/) are discovery leads. Reviewed open
PRs #3407/#3661/#3835/#4080 do not supply this strafe visibility gate. PR #3407's
separate phase-classification fix remains deferred; none of its code is copied.

Human play check: in an isolated End arena, let the dragon select a survival target
for strafing. Hold solid cover between the dragon and the target: it should not
complete its ranged attack while occluded. Clear the view: five charging ticks
should permit the attack. Interrupt a partially charged attack with cover: the
charge should decrease, delaying the attack after sight returns. Capture a real
client recording of cover, emergence and attack timing before any upstream PR.
