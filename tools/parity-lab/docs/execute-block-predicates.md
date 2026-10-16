# Execute block state and tag predicates

## Reproduction

Baseline: campaign head `4e8a17f0741b7193c4a50be08d964fb3c16ef381`, containing fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844`; upstream master remains `5b53f064af8708ba33fcaa533b81ca29a53a3310`.

With an oak log at `2 80 2`, vanilla 26.3 accepts `execute if block 2 80 2 minecraft:oak_log[axis=y]` and reports `Test passed`. The campaign baseline rejects the state suffix as trailing data. `#minecraft:logs` and tag state filters are likewise rejected. Plain block-name controls work.

Two scratch-server repetitions in `artifacts/jaron-block-predicate-live-20261016T072058.735693Z/report.json` produced vanilla 96/96 observations and baseline 30/96. Checks include terminal feedback and scoreboard-observed continuation gating, both condition polarities, cross-material tag matches, absent/invalid tag properties, partial stair state predicates and an NBT predicate on a block without an entity. Both scratch servers stopped; no source-console error/panic lines occurred. These observations use RCON for vanilla and scratch stdin/stdout for Pumpkin, without connected clients.

## Correction and source comparison

Use the existing `BlockPredicateArgumentType` in the two execute block branches. Test actual state IDs with `BlockPredicate::test_state`, preserving the distinction between unspecified and specified properties. Apply the same test to terminal execution and command continuation, with opposite results for `if` and `unless`. Optional block-entity NBT uses full metadata from `write_internal` and the existing NBT subset comparator; a missing entity cannot match an NBT predicate.

Compared vanilla `ExecuteCommand.addConditionals`, `BlockPredicateArgument.BlockPredicate.test`, `TagPredicate.test`, `BlockInWorld` and `NbtUtils.compareNbt` from the official 26.3 jar, decompiled privately with Vineflower 1.12.0. The vanilla sources, jars and runtime evidence are not committed.

Issue #2592 documents broader execute/block gaps. Open PR #3827 changes setblock state parsing, while #3987 changes execute score storage; neither contains this predicate registration/evaluation correction. No upstream messages or PRs were created.

## Validation status

The Rust regression failed before the correction on the expected `command.expected.separator` syntax assertion. After correction, all 443 core unit tests, workspace formatting, core all-targets/all-features clippy and the full binary build passed. All Cargo operations ran under the shared build lock, one job, disabled debug info/incremental compilation, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. The existing proc-macro-error2 future-incompatibility notice remains. Results: `artifacts/jaron-block-predicate-verify.json` and `artifacts/jaron-block-predicate-build.log`.

Patched live comparison `artifacts/jaron-block-predicate-live-20261016T073029.516005Z/report.json` repeated the same checks twice: vanilla and patched Pumpkin each passed 96/96 observations. Terminal feedback matched exactly; scoreboard observations verified both successful and suppressed continuations. Both scratch servers stopped, with no ERROR/panic lines in either console log. The binary SHA-256 is `b5d59eaa078d665f8dc808f2e0508601a68591bfa18fb6bbf97d25b5db5def92`. Completion assertions are retained in `artifacts/jaron-block-predicate-completion.json`.

## Limits and next candidates

This patch does not correct unloaded/out-of-world block-position errors. The existing shared predicate parser still accepts some invalid named-block properties instead of producing vanilla parse errors. The existing NBT-path comparator lacks vanilla 26.3's list-cardinality guard; that is a separate command-owner correction. Positive live block-entity NBT, real clients, packet suggestions and full RCON coverage remain untested.

Next owned candidates: reproduce unloaded/out-of-world execute block errors, or add a bounded missing terminal condition family such as loaded/dimension/biome/data. These are leads, not confirmed completed bugs. Passing this bounded suite would not establish full Minecraft parity.
