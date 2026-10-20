# Wither retaliation block traversal order

A damaged Wither scans a cuboid after its 20-tick retaliation delay. Pumpkin visited Z first, then Y, then X. Vanilla visits X first, then Y, then Z. This changes the observable order of block destruction effects across the cuboid.

The Wither-only Rust correction uses the existing `BlockPos::between_closed_coords` iterator with the same inclusive bounds. Block eligibility, block-break API, drop flags and successful-break sound gating stay in their existing path.

## Reference and overlap

Minecraft 26.3 `WitherBoss.customServerAiStep` calls `BlockPos.betweenClosed`. The server's `BlockPos$4.computeNext` uses X as the fastest coordinate, then Y, then Z; verified from the local official inner jar bytecode. No decompiled source or jars are committed. Current upstream `fb7c8e223` retains the old loop order. Fork master `65bca3f7f` is already an ancestor of the campaign branch; no merge needed.

The tracker and Mob AI tracking issue 3468 were checked as leads. Open PR 4092's Wither changes do not alter the retaliation traversal; its healing/bossbar correction was excluded as overlapping. Reviewed related 3835, 3865, 4105, 4107 and 4112 scopes. No equivalent traversal correction found.

## Focused regression

`lab/examples/wither-retaliation-block-order.json` defines six isolated sealed-cell cases: eight separated stone blocks, immune bedrock, and disabled mob griefing, each repeated twice. It advances 19 ticks without destruction, then one tick for the retaliation pulse, and repeats on the resulting cuboid; the stone cases now have only air in those eight positions. A protocol 777 headless observer captures exact block destruction positions, count, kind and audience and the boss break-event count. The report checker is `tests/check_wither_retaliation_block_order.py`.

Vanilla and patched Pumpkin each passed 162/162 checks. Baseline `d0fd75db7` passed 160/162: only the two exact order assertions fail, with the expected Z-fastest sequence. Each target ran 416 verified controlled ticks including cleanup. Fixture/stimulus, source and copied-binary hashes, cleanup, server stops and clean server/client logs checked. Local detailed evidence: `artifacts/jaron-wither57-validation.json` and `artifacts/jaron-wither57-source-provenance.json`.

Workspace formatting, all 444 core Rust library tests, core all-target/all-feature Clippy and the debug server build passed under the shared Cargo lock and resource limits. Existing `proc-macro-error2` future-compatibility warning remains. Patched source hash: `811940038880033998139d1d8bbc31fc00ab91e02319e0a72b26906bb222770d`; copied debug binary SHA-256: `cd4828d5dde8fdb8342f03ee1f27f3b8214f4e79bba17df817be1e29633d9dd0`.

## Limits and manual observation

This is command-controlled retaliation with NoGravity and a headless protocol observer. It does not prove natural combat, a whole boss fight, rendered particles/audio, support-loss cascades, item drop ordering, Bedrock or plugin listeners. Regression coverage is the isolated world fixture; no new isolated Rust unit test is claimed.

For visual observation, place separated blocks around a stationary Wither in an isolated arena, damage it, and record the retaliation effects. No rendered-client capture is available or claimed.
