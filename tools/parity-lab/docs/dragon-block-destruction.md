# Ender Dragon block destruction permissions

The dragon block-breaking loop ignored `mob_griefing` and protected only six hardcoded block types. Vanilla 26.3 `EnderDragon.checkWalls` excludes air and `dragon_transparent`, then permits destruction only when the gamerule is enabled and the block is outside `dragon_immune`.

Source commit `9fff3648b5303d94ca48232c4f64cbc7981fcfc2` uses the generated tags and current world gamerule for that decision. It preserves the existing block update path. The helper is private to the dragon and called only by its block-breaking loop. All six previous exclusions are included in `dragon_immune`. The baseline dragon source was identical to upstream master `5b53f064af8708ba33fcaa533b81ca29a53a3310`.

Two focused Rust regressions failed on the original predicate: stone was destructible with griefing disabled, and barrier was destructible with griefing enabled. The corrected source passed:

- `cargo test --locked -p pumpkin-core --lib`: 447 tests, including both regressions.
- `cargo fmt --all -- --check`.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`.
- `cargo build --locked -p pumpkin`.

All Cargo commands used the shared lock, one job, disabled debug info/incremental compilation and systemd memory/CPU limits. Only the existing `proc-macro-error2` future-compatibility warning appeared. Binary SHA-256: `6b322b32afd5f51752a079b5d59bcad89f4064ce2dd9bbb1c14d6491182b886a`.

The isolated live comparison ran vanilla 26.3, the current-source baseline binary and this patched binary under the shared engine lock, twice per server. For each gamerule value it placed stone, barrier, end stone and light inside a ticking persistent dragon's contact volume. Every block was verified present before advancing two simulation ticks; game-time barriers verified the requested advancement. Ordinary stone with griefing enabled disappeared on all three servers, establishing active block breaking.

Vanilla and patched Pumpkin passed all 16 gameplay observations each. The baseline failed the same five cases in both trials: stone, barrier and light with griefing disabled, plus barrier and light with griefing enabled. End stone remained intact in both rule states. All 48 precondition observations passed, no final setup command reported an unloaded chunk or syntax error, all scratch servers stopped normally, and their logs contained no ERROR or panic lines. No observations or expectations changed between targets.

Evidence remains outside Git in the deployment workspace: `artifacts/christine-dragon-red.{log,json}`, `artifacts/christine-dragon-rust-validation.json`, `artifacts/christine-dragon-live-20261016T075526.862924Z/report.json` and `artifacts/christine-dragon-final-validation.json`. Preliminary reports are retained: namespaced gamerule syntax, an inactive initial positive control, unsupported fire extinguishing and scratch chunk unloading made those attempts inconclusive. The final temporary probe retained the existing GameTest arena throughout the run; no lab infrastructure source was changed.

Upstream overlap inspection excluded PR3407 (part dimensions, damage, healing and phase classification) and PR3661 (part entity lookup). Neither changes block destruction. A final dragon/grief PR search found only the original closed AI ports. Fork master and upstream master were fetched before editing and again before publication; fork master is already an ancestor of this branch.

This patch corrects which blocks the current loop may destroy. Main-box versus part-box coverage, sitting-phase behavior, `in_wall` updates and destruction particles remain unaddressed. The collision gates in tracking issue #3468 remain a separate source-confirmed lead. No connected-client or visual proof, full boss fight, or full parity claim.
