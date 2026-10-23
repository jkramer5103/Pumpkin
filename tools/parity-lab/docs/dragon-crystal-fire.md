# End fight crystals restore extinguished fire

End Crystals in a dragon-fight world now restore fire at their feet when that block is air. Vanilla `EndCrystal.tick` calls `BaseFireBlock.getState` and `setBlockAndUpdate`; Pumpkin had no crystal tick override. The new override preserves the existing base entity tick, then uses the existing fire type and placement-state helpers. It chooses soul fire over soul sand or soul soil, preserves occupied blocks, and does nothing outside a dragon-fight world. The existing cancellable `BlockIgniteEvent` runs before placement with the selected fire type and no player.

## Bounded reproduction

Official Minecraft 26.3 and the immutable campaign-80 Pumpkin binary were exercised by the identical isolated arena probe with a live headless player. Each of seven cases was sampled twice after exactly one controlled tick. Vanilla restores ordinary fire over bedrock and soul fire over both soul bases; the baseline leaves air in all six samples. The eight occupied-stone, occupied-water, existing-fire and Overworld-air controls agree. Crystal presence, unchanged support blocks, removal followed by absence of relighting, player presence, cleanup and stopped-process checks pass. The regression checker passes official and deliberately fails baseline.

The final source passed all 493 pumpkin-core Rust library tests, workspace formatting, core Clippy with all targets and features, and a debug server build under the shared Cargo lock and resource limits. Patched Pumpkin matches vanilla in all 14 samples, correcting the six baseline failures. All 194 post-setup stimulus commands are identical, and each target advances exactly 248 controlled ticks including cleanup. Source, binary, official reference, probe, fixture, checker, report, client packet and server/client log hashes are verified; the successful logs contain no errors or panics. Existing startup notices and the proc-macro-error2 future-compatibility warning remain.

## Coverage and limits

The fixture and checker are `fixtures/dragon-crystal-fire/cases.json` and `tests/check_dragon_crystal_fire.py`. Local evidence is recorded in `artifacts/christine-dragon81-{before-validation,live-validation,rust-validation,source-provenance,prepush-overlap,fire-overlap}.json` in the deployment workspace. Source, binary, official reference, probe, fixture and report hashes are retained there; no jars, worlds or decompiled source are committed.

This is server block-state and headless protocol evidence, with no rendered-client, Bedrock, reload, natural whole-fight or full ritual-completion proof. The sample crystals are command placed with invulnerability and portal cooldown to isolate fire creation. Fire spread, unsupported fire, neighbor attachment shapes and removal of occupied blocks are outside the bounded probe. No plugin is installed, so cancellation is covered by source review and compilation only. The baseline is campaign80; current upstream retains the missing tick override, but no separate upstream-master binary is claimed.

Read-only upstream searches on 2026-10-23 found no open spike/pillar or crystal-fire implementation. Tracking issue 3468 and PRs 3661/3407/3694 were reviewed as leads; multipart damage, crystal healing, despawn and explosion overlap remain deferred. This patch changes only crystal fire restoration.

A superseded fixed-binary attempt stalled during initial End chunk setup, before any gameplay sample, and was stopped and excluded. An intermediate event-hook compile error was corrected before the final passing checks. Neither attempt contributes passing evidence.
