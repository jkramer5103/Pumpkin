# Constructed Wither spawn height

With a structure base at (15,81,15), vanilla 26.3 sends its constructed Wither at (15.5,81.55,15.5). The prior Pumpkin campaign binary sends (15.5,82.5,15.5), putting the boss 0.95 blocks too high before subsequent simulation. The correction retains the base block in WitherPattern and uses its centered X/Z plus vanilla's 0.55 Y offset before entity construction. This also gives the entity bounding box and existing spawn event the corrected position. Structure consumption and invulnerability initialization retain their existing ordering.

Reference: WitherSkullBlock.checkSpawn uses match.getBlock(1,2,0) and snapTo(baseX+0.5,baseY+0.55,baseZ+0.5). Entity::new stores the position and builds its bounding box; WitherEntity::new and make_invulnerable do not relocate it. The pattern helper's dispenser caller only checks for presence and does not use the private base field.

The focused wither-construction-height.json fixture requires a connected creative headless client to place the final skull at each of three positions, in both horizontal orientations. Its packet assertion uses the observed vanilla position before tick-driven movement. Seven consumed blocks, absence before placement, presence after placement, loaded-client delivery, operator/client state, cleanup and identical stimuli are controls. Two trials per case are required by the external probe.

Rust validation passed under the shared build lock with one Cargo job, disabled debug info and incremental compilation, and a 5GiB/zero-swap/200%CPU systemd scope:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib` (444 passed)
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

Two trials of six cases passed on vanilla and the patched binary: 192/192 checks each. Baseline passed 180/192, with exactly the 12 spawn-height assertions failing. All baseline spawns used Y=82.5; all vanilla/patched spawns used Y=81.55. Each target advanced 349 controlled ticks including cleanup. Fixture, gameplay-command, source and copied-binary hashes matched. All three scratch processes stopped and cleanup passed; both Pumpkin saves and stops completed. Final server/client logs contained no ERROR, panic or uncaught-thread-exception lines.

Evidence is retained outside the repository in `artifacts/jaron-wither48-height-validation.json`, `artifacts/jaron-wither48-height-verify.json` and the per-target reports on the deployment workspace. The copied patched binary SHA-256 is `e63c2598b41bae0ec3ba387ac7224f478dd38d7b95ea7aca7d3ed8e2159ca144`.

The scenario is the regression coverage; no isolated Rust unit test was added. Existing `proc-macro-error2` future-compatibility warning remains.

Limitations: headless protocol777 and server-state evidence only. No rendered-client, whole-fight, Bedrock, reload, dispenser, wall-skull or live plugin-listener validation. Spawn rotation remains a separate known source discrepancy and is not corrected here. Vanilla final save completion needs separate confirmation; stopped processes must be checked.

Upstream overlap checked on 2026-10-19: fork master is already an ancestor; current upstream still uses the upper soul-block center. Read 313 open PRs and relevant Wither/summoning file lists; no matching construction-file change found. Maintainer tracking issue3468's spawn-invulnerability goal is already implemented by an earlier campaign patch. Shared AI/flight, projectile and death proposals remain outside this change.
