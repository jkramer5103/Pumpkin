# Wall skulls in Wither construction patterns

A structure with existing wall-mounted Wither skeleton skulls should summon a Wither when a player places the final floor skull. Pumpkin's matcher only accepted existing floor skulls. Vanilla 26.3 `WitherSkullBlock.getOrCreateWitherFull` accepts either Wither skull block in each of its three skull slots. The Rust correction adds the wall variant to that predicate and keeps the prospective final-skull exception used by dispensers.

The two callers remain `WitherSkeletonSkullBlock.placed` and `DispenserBlock.dispense_mob_head`. The former keeps the difficulty gate, seven-block removal, spawn event, position/rotation and invulnerability setup. The latter only tests pattern eligibility; this change recognizes existing wall skulls there too. Dispenser base-pattern semantics and actual spawning are separate candidates. Final wall-skull placement is also outside this patch: it needs its own placement/registration reproduction.

The focused `wither-construction-wall-pattern.json` regression uses default-state existing wall skulls, then a connected loaded/operator creative client places the final floor skull. Both horizontal axes cover one wall skull, two wall skulls and floor-only controls. A different skull species and Peaceful difficulty must preserve the structure. Each case checks all seven structure blocks, three retained adjacent stone blocks, boss presence, the spawn packet position/rotation, invulnerability ticks, actual placement packet, player/client state and cleanup. The scenario's `PARITY_BUILD_PLACE` marker requires that client; console-only execution does not perform placement. Setup checks verify the two existing skulls before placement. Two trials run with frozen time and exactly controlled ticks.

The corrected immutable reference passed 452/452 checks on vanilla and 356/452 on baseline Pumpkin. Exactly 96 failures occur in the eight wall-skull positive rows; all setup, client, placement, environment, floor-only, wrong-species and Peaceful controls pass. Each target ran 20 rows and 565 controlled ticks. Cleanup and process stop passed, Pumpkin save/stop markers were present, and final server/client logs had no errors or panics. Initial explicit-facing exploratory fixtures were excluded because Pumpkin rejected their setblock properties; both targets were rerun with the corrected default-state fixture.

Rust validation passed under the shared Cargo lock with one build job, disabled debug info and incremental compilation, and a 5GiB/zero-swap/200%CPU scope:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib` (444 passed)
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

The patched server passed 452/452 checks with the same fixture and gameplay-command hashes as vanilla and baseline. All three scratch processes stopped and cleanup passed. Both Pumpkin saves/stops completed, and all final server/client logs were free of ERROR, panic and uncaught-thread-exception lines. Source hashes and the copied binary match the Rust verification record. The copied patched binary SHA-256 is `fd099902683f509209d3aa6141a4784faa717b3f40b2564f92ec6c15fef58c0b`. The existing `proc-macro-error2` future-compatibility warning remains. Local task evidence is retained in `artifacts/jaron-wither50-wall-pattern-validation.json`, `artifacts/jaron-wither50-wall-pattern-verify.json` and the per-target reports in the deployment workspace. These checks provide bounded evidence for this construction behavior.

Fork master was fetched and is already an ancestor of the lane branch. Current upstream retains the same floor-only matcher. A fresh authenticated review of 313 open PRs and relevant full file lists found no overlapping Wither construction patch. Existing AI, projectile and death/drop proposals remain deferred. The maintainer tracking issue's invulnerability-window goal was fixed in an earlier campaign commit and was not reworked here.

Limitations: headless protocol777 and server-state evidence only; no rendered client, complete boss fight, final wall-skull placement, dispenser spawning, Bedrock, reload or plugin-listener proof. Focused world scenario regression, without a new isolated Rust unit test.
