# Wither retaliation block drops

Source and regression fixture: `3171a924013c9f20175f1d4dc59a624c9ae24903`.

A damaged active Wither previously replaced nearby blocks with air after its
20-tick retaliation delay. That removed dirt without creating its item. Vanilla
26.3 removes the block and drops one dirt item. Both repetitions of the same
isolated arena confirm this difference.

The source change in `crates/pumpkin-core/src/entity/boss/wither.rs` calls
`World::break_block` instead of `set_block_state`. This reuses the block loot,
block-break/drop plugin events, fluid replacement and break effects. The Wither
passes `SKIP_DROPS` when `block_drops` is disabled because the shared helper does
not itself enforce that rule. The existing mob-griefing gate, retaliation timer,
destruction volume and Wither-immune block predicate remain in place. The
aggregate destruction flag now depends on the break helper succeeding, including
its cancellation result. No shared source file or caller is changed.

## Vanilla and overlap

Reviewed the official 26.3 server's decompiled `WitherBoss.customServerAiStep`,
`Level.destroyBlock`, and `Block.dropResources`/`popResource` outside the repository.
Vanilla destroys eligible blocks with resources enabled and an empty tool;
`Block.popResource` and experience drops respect `BLOCK_DROPS`.

Fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` (already an ancestor)
and upstream master `b57d821decdabcfadf300abfb2061ac0ad3cfd21`.
The current upstream Wither source still uses direct air replacement.
[Mob AI tracking](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and the
[parity tracker](https://pumpkinmc.org/tracker/) were treated as leads.
The refreshed open-PR search found no equivalent retaliation fix.
[PR 3865](https://github.com/Pumpkin-MC/Pumpkin/pull/3865) covers death/star drops;
[PR 3835](https://github.com/Pumpkin-MC/Pumpkin/pull/3835) covers projectile flight
and direct-hit attribution. Neither changes this retaliation path.
Merged PR 4038 covers effect immunity and is outside this patch.

## Focused regression

`lab/examples/wither-retaliation-block-drops.json` holds the reproducer.
Each scratch server has one connected creative protocol-777 headless client,
forceloaded bounded chunks, easy difficulty, no natural spawns or attack targets,
and an active, silent, gravity-free Wither. Generic damage starts the retaliation
without an explosion. The fixture repositions the boss before each verified tick
to isolate block destruction from wandering.

The checks verify dirt survives through tick 19 with no items, then disappears
and produces a dirt item at tick 20. Adjacent bedrock and out-of-range dirt survive;
no skull exists. Repeat the same stimulus with `mob_griefing=false` (no destruction
or item) and `block_drops=false` (destruction, no item). Run all three cases twice.
The overrides are applied after setup and before damage.

Baseline binary: `pumpkin-jaron-wither18-fixed`, SHA-256
`20c5b3a82bd1a59df5aad00142faaa2b9586aca5c4afd81626e2b4d2f0367920`,
source commit `5d87e9bbd01f3f1bdebf33878f6ea95b5aae7e40` with documentation head
`38290facca7ac0a85337700aaadf118948e47a5e`.
Fixture SHA-256: `ec4e19feb72e52baa38c91cecf442ce24408807bec4ac7c6e3bfea387ba0c83e`.

Baseline: **70/72**; only the two positive drop observations fail.
Vanilla and patched Pumpkin: **72/72** each. Raw evidence remains outside the repository:

- `artifacts/jaron-wither19-baseline-20261016T215020.375711Z/report.json`
- `artifacts/jaron-wither19-vanilla-20261016T215050.949457Z/report.json`
- `artifacts/jaron-wither19-reference-validation.json`
- `artifacts/jaron-wither19-fixed-20261016T220558.125385Z/report.json`
- `artifacts/jaron-wither19-validation.json`

Rust validation passed: workspace formatting, all **443** core library tests,
`cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
`cargo build --locked -p pumpkin`. All Cargo operations ran under the shared
build lock with one build job, disabled debug info/incremental compilation,
and a 5 GiB, no-swap, 200% CPU scope. The earlier interrupted build is excluded;
`artifacts/jaron-wither19-build.exit` records exit 0 for the persistent rerun.
The existing dependency future-compatibility warning for `proc-macro-error2`
remains; no new clippy warning was reported.

Patched binary: `pumpkin-jaron-wither19-fixed`, SHA-256
`b7bab9d6cc301b79e2a546eed70026279460db0e855dee3ac01adb3e74771377`.
The source file SHA-256 checked against the build and committed patch is
`15c47f6c95c51dc59607609b4279390e14a9ff17cb87e5038628dc2de092c76b`.

Final assertions confirm identical fixture and stimulus-command hashes for each
case across all three servers, exact tick deltas at all 22 barriers per case,
client presence, clean server stops, and no ERROR/panic log lines. The two
positive-drop trials contain exactly one dirt item with count 1 on vanilla and
patched Pumpkin; all negative controls have no item. Baseline lacks that item.
Baseline and patched binary provenance were verified against the build records.
The complete result is 70/72 baseline, 72/72 vanilla, and 72/72 patched.

## Limits and manual check

This is headless server-state proof, not client visual or whole-fight proof.
The fixture covers one dirt item, timing, gamerules and protected/range
controls. Other loot tables, block entities, waterlogging, experience amounts,
pickup delay and plugin cancellation are not individually exercised. Reusing the
shared break helper also retains its existing limitations, including missing
Wither attribution in its player-oriented cause parameter.

Before any upstream submission, use a real 26.3 client in a disposable arena:
place dirt beside an active Wither, damage it once and confirm destruction and a
pickupable dirt drop after twenty active AI ticks. Confirm protected bedrock
survives and disabling mob griefing prevents the break. The human must create any
upstream PR; no automated upstream publication is authorized.
