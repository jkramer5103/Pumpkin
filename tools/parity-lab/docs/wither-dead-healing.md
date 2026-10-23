# Healing during Wither death

A splash harming potion could raise a dead Wither's health from zero to four. Because the shared death timer advances only at zero health, the boss then remained in the world after the normal 20-tick death animation. Ordinary healing now returns when the living entity's health is zero, matching official `LivingEntity.heal`. Positive-health healing retains the existing cancellable health-regain plugin event and health update path. This covers potion, regeneration, food, dragon-crystal, Wither spawn/regeneration/skull-kill, player-wrapper and animal-interaction callers; dead targets now ignore these heals. Direct `set_health` calls, including deliberate resurrection mechanics, are unchanged.

Official 26.3 `ThrownSplashPotion.applySplash` skips dead targets through `LivingEntity.isAffectedByPotions`; official `LivingEntity.heal` also independently requires positive current health. Pumpkin's splash candidate path currently includes corpses and its shared healing method lacked that guard. This bounded correction protects the shared healing method. General potion eligibility and duration effects on corpses remain separate work. The official source was inspected locally; decompiled Java stays outside Git.

Exploratory isolated arena runs used the same fixed boss UUID, real client item-use packets, a splash harming projectile moved to the bedrock floor, and a lethal `generic_kill` hit before impact. Official health stayed zero and the corpse disappeared; campaign 84 Pumpkin changed from zero to four and was still queryable after 21 ticks. No source defect was inferred from an infrastructure failure.

Focused regression coverage is in `fixtures/wither-dead-healing/cases.json` and `tests/check_wither_dead_healing.py`. Ten cases run twice: fresh/mid-animation Wither corpses, harming I/II, charging Wither, water, sheep and zombie corpse controls, injured living targets, and a Wither at one health. The checker requires exact health and death-time samples, presence at tick 19 and removal at tick 20 for corpses, living controls, real item use/projectile/splash packets, positions, spawn timer, client, cleanup and stopped-process checks. UUID queries include corpses that ordinary selectors omit. At tick 20, the probe waits 0.4 seconds while simulation is frozen, verifies unchanged game time, and then queries removal. The initial comparison raced deferred removal in one fixed sample: its next same-frozen-tick query already found the corpse absent and the death-particle packet was present. That initial matrix is excluded; all three targets were rerun with the same settling pause. Between cases, all targets receive identical health-reset cleanup commands so a reproduced stuck baseline corpse cannot contaminate the next case.

Workspace formatting, all 450 core Rust library tests, core all-target/all-feature Clippy and the debug server build passed. Cargo ran under the shared build lock with one job, disabled debug information/incremental compilation, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. Official 26.3 and patched Pumpkin each pass 521/521 focused arena checks; the campaign 84 baseline passes 473/521, failing exactly 48 health, stalled-death-time and corpse-removal assertions across six dead-target cases in both trials. Water and living-target controls agree. Each target ran 1,052 controlled ticks with identical probe, client, fixture and gameplay commands. Cleanup, stopped-process and error-log checks pass. Source, binary, official-source, checker, probe, fixture, report, packet and log hashes were verified. The existing proc-macro-error2 future-compatibility notice remains. The regression exercises real world/entity/projectile paths; no mocked healing setter test or new Rust unit test is claimed.

Fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor. Upstream `9c04f714bb7eb26579c652f9744895d465ee902b` still heals unconditionally. Reviewed open PR patches #3835, #3816, #3663, #4117, #4174, #4050, #3988, #4173, #4175 and #3865 contain no positive-current-health guard in ordinary healing. Totem protection #4117 deliberately sets health directly, and remains separate. Projectile geometry/attribution and Wither drop timing remain deferred. The pre-push refresh found no new or changed PR heads. The new #4179 projectile hit-block patch was also inspected and does not overlap healing.

Limits: headless protocol/server-state evidence only; no rendered-client, Bedrock, natural-fight or whole-fight proof. NoAI/NoGravity isolates health and death timing. Real projectiles are moved to target feet; geometry, indirect damage ownership, and other effect delivery paths are outside the measured fixture. No plugin is installed, so plugin cancellation is preserved in source but not exercised. The baseline is the provenance-checked campaign 84 binary, not a separately built upstream-master binary. Logs, worlds, jars and runtime probes stay outside Git.

Lead sources: [tracker](https://pumpkinmc.org/tracker/) and [mob AI tracking](https://github.com/Pumpkin-MC/Pumpkin/issues/3468). Previously completed spawn-window goals and source patches were not reimplemented.

Evidence: `artifacts/jaron-wither85-{live-validation,source-provenance,rust-validation,overlap}.json`.

## Dеscription ·

> This description was drafted by an AI agent (Codex, gpt-6.1-sol).

Prevent ordinary healing from raising a dead entity's health and interrupting corpse removal. A dead Wither hit by splash harming remains dead and completes its death animation, while a living Wither still heals.

## Tеsting ·

The 450 Rust tests, formatting, Clippy, build and 521/521 official/patched arena checks pass; the baseline reproduces 48 focused failures. Before any human opens an upstream PR, use a bounded scratch arena and a real client: kill a Wither, immediately splash harming on the dying boss, and expect it to disappear after its death animation. Repeat with a living injured Wither and expect healing. Record the potion impacts and both outcomes. Keep the AI disclosure unless the author rewrites the description.

Capture: <attach screenshot or recording here>
