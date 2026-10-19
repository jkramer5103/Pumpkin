# Constructed Wither facing

A Wither constructed from a T with east/west arms should start at yaw90; north/south arms should start at yaw0. Pumpkin previously initialized both cases at yaw0. The patch keeps the matched pattern yaw and assigns it to entity yaw and body yaw before boss construction and world registration.

Vanilla 26.3 `WitherSkullBlock.checkSpawn` passes a pattern-dependent yaw to `Entity.snapTo`, then assigns the same value to `yBodyRot`. The pattern forward axis is perpendicular to its horizontal arms. `snapTo` does not set head yaw; the patch likewise preserves independent head state. Pumpkin's mob/living constructors retain the entity fields, and the world tracker snapshots the initial yaw for AddEntity. Existing structure removal, spawn event and invulnerability initialization keep their ordering. The other caller of `find_wither_pattern`, dispenser eligibility, only checks whether a pattern exists.

The focused `wither-construction-rotation.json` regression needs a connected creative client to place the final skull. Both arm axes and each final-skull position are exercised twice. The checks observe actual Wither spawn-packet yaw/pitch and Rotation NBT after two controlled ticks. Spawn position, presence/absence, seven consumed blocks, client loaded/operator state and cleanup are controls. A console-only runner cannot perform the placement marker.

Rust validation passed under the shared Cargo lock with one build job, disabled debug info/incremental compilation and a 5GiB/zero-swap/200%CPU scope:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib` (444 passed)
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

Vanilla and the patched binary each passed 216/216 focused checks. Baseline passed 204/216, with exactly six spawn-packet yaw failures and six server Rotation failures for east/west-arm structures. Both trials covered all three final-skull positions in both orientations; each target advanced 349 controlled ticks including cleanup. All controls passed. Fixture and gameplay-command hashes matched across all targets; source and copied-binary hashes matched the Rust validation record. All three scratch processes stopped and cleanup passed; both Pumpkin saves/stops completed. Final server/client logs contained no ERROR, panic or uncaught-thread-exception lines.

Evidence is retained on the deployment workspace in `artifacts/jaron-wither49-rotation-validation.json`, `artifacts/jaron-wither49-rotation-verify.json` and the per-target reports. The copied patched binary SHA-256 is `8b244ba4fe2c1065eba39ba0dc9b5129d6a4124bd46ed965600b0ff56528292b`. An initial formatting check failed and was corrected before the final full successful validation. Existing `proc-macro-error2` future-compatibility warning remains.

Upstream/fork state was fetched on 2026-10-19. Fork master 65bca3f7 is already an ancestor. Upstream fb7c8e223 still has the zero-yaw constructor path. The final authenticated overlap check read 313 open PRs and the relevant Wither/skull/summoning/dispenser file lists without errors; no construction-file overlap was found. Evidence: `artifacts/jaron-wither49-final-overlap.json` on the deployment workspace. Shared AI/flight, projectiles and death proposals are separate. The maintainer tracking issue's spawn-window goal is already fixed by an earlier campaign commit.

Limitations: headless protocol777 and server-state observations only. No rendered-client, full-fight, Bedrock, reload, dispenser, wall-skull or live plugin-listener proof. In particular, head/body visual interpolation has not been checked. Vanilla final-save completion was not verified; its stopped process was checked. The world scenario is the regression coverage; no new isolated Rust unit test.
