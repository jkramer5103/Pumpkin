# Zero-point Wither healing

A weak splash harming potion can round its inverted healing amount to zero. `LivingEntity::heal` previously asserted that the amount was strictly positive, panicking on the server ticker and shutting down the scratch server. Removing that assertion lets zero-point healing proceed through the existing health-regain plugin event and health setter. Positive healing keeps the same path.

Official 26.3 `HealOrHarmMobEffect.applyInstantaneousEffect` rounds the scaled amount and calls `LivingEntity.heal` even when it is zero. The official living method accepts that amount. The decompiled Java remains outside Git. Existing positive callers include regeneration, hunger, consumption, player wrappers, dragon crystals, Wither spawn/regeneration/skull-kill healing, dolphins, wolves and cats. Their calculations and events are unchanged; the shared method now also accepts the zero result produced by potion rounding. Dead-entity healing is a separate concern outside this correction.

Before the patch, a real client-thrown splash harming potion placed 3.8 blocks from an injured NoAI Wither caused the campaign 83 binary to panic at `living.rs:780`, with `PotionContents::apply_effects_to` and splash-potion impact in the crash backtrace. Vanilla continued normally. This also exposed an existing splash falloff difference: vanilla measures hitbox distance and healed the injured boss by one point, while Pumpkin measures center distance and rounded to zero. This patch addresses the panic; it does not fix that geometry difference or claim injured edge-health parity.

The retained regression fixture uses full-health edge targets so small vanilla healing and zero Pumpkin healing both leave health capped, while a baseline panic still fails continued-tick checks. It covers Wither harming I/II at 3.8/3.9 blocks, charging Wither, sheep healing and zombie harming edge controls, injured Wither and sheep direct-hit positive healing, and water. Each of nine cases runs twice in an isolated bedrock arena with real item-use packets and splash projectiles moved to the floor. The checker requires continued ticks, splash packets, projectile removal, health, position, Invul, player/client/arena controls, cleanup and stopped processes. This is world/entity regression coverage; the GameTest helper currently provides block operations, and no mocked entity unit test is claimed.

Workspace formatting, 450 core Rust library tests, core all-target/all-feature Clippy, and the debug server build passed under the shared Cargo lock, one build job, disabled debug information/incremental compilation, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. Official 26.3 and patched Pumpkin each pass 353/353 focused checks over 618 controlled ticks. The campaign 83 baseline crashes on the first full-health edge-harming case, reproducing the exact healing assertion and splash-impact backtrace; its incomplete report is recorded as expected failure, not a completed suite. Vanilla and patched runs execute identical probe/client/fixture/gameplay commands; the baseline matches their command prefix through impact. Source, binary, fixture, checker, official-source, report, packet, log and baseline crash hashes were verified. Successful runs clean up and stop without errors or panics. The existing proc-macro-error2 future-compatibility warning remains.

Fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor. Upstream `9c04f714bb7eb26579c652f9744895d465ee902b` still contains the same positive-healing assertion. Relevant open PR file patches #3835, #3816, #3988, #3663, #4174, #4050, #4117, #4173 and #4175 contain no zero-healing correction. The pre-push scan found no new PRs or changed heads. PR #3835 and neighboring potion work remain overlap leads for separate geometry/attribution changes.

Limits: headless protocol/server-state evidence only; no rendered-client, Bedrock, natural-fight or whole-fight proof. Full-health edge cases isolate survival/tick continuation, not falloff correctness. The baseline is the immutable provenance-checked campaign 83 binary; no separate upstream-master binary is built. Plugin cancellation remains wired but no plugin was installed in this arena. Logs, jars, worlds, runtime probes and decompiled Java stay outside Git.

Lead sources: [tracker](https://pumpkinmc.org/tracker/) and [mob AI tracking](https://github.com/Pumpkin-MC/Pumpkin/issues/3468). Completed spawn-goal fixes were not reimplemented.

Evidence: `artifacts/jaron-wither84-{live-validation,source-provenance,rust-validation,overlap}.json`.

## Dеscription ·

> This description was drafted by an AI agent (Codex, gpt-6.1-sol).

Allow zero-point healing so weak splash harming potions near Withers do not shut down the server. Keep the existing health-regain event and health update path.

## Tеsting ·

The 450 core Rust tests, formatting, Clippy, build and 353/353 official/patched arena checks pass; the baseline reproduces the panic. Before any human opens an upstream PR, join a bounded scratch arena with a real client, throw weak edge splash harming potions near a Wither, and confirm the server keeps running and positive direct-hit healing still works. Record the throw and continued gameplay. Keep the AI disclosure unless the description is rewritten by the author.

Capture: <attach screenshot or recording here>
