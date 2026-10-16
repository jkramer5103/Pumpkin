# Decreasing selector rotation bounds

Vanilla 26.3 accepts `y_rotation=170..-170`, selecting angles on either side of the signed boundary, including both endpoints. Pumpkin rejected the command with `Min cannot be bigger than max` before evaluating the selector. The same parser rejection affected `x_rotation`.

The comparison baseline is source commit `9a3a5f9d6acf17a5df63b90d39510a75bb6c42d4`, which already includes the previous axis fix. Current upstream `5b53f064af8708ba33fcaa533b81ca29a53a3310` has the same swapped-range rejection in `pumpkin-command`. Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is an ancestor; the existing terminal execute fix `4e8a17f0741b7193c4a50be08d964fb3c16ef381` was merged without rewriting history.

Vanilla call chain checked: `EntitySelectorOptions` parses both rotation options with `MinMaxBounds.FloatDegrees.fromReader`; it constructs degree bounds directly after `Bounds.fromReader`. In contrast, the integer and double implementations explicitly reject swapped bounds. `EntitySelectorParser.createRotationPredicate` wraps the endpoints and performs an inclusive OR when the wrapped minimum exceeds the maximum. Pumpkin already has that matching logic. The source correction removes only the degree parser's swapped-range rejection; it preserves endpoint order and leaves integer/double validation untouched. The only production callers of this degree parser are the two selector rotation options.

The focused selector regression parses decreasing signed-boundary and zero-crossing bounds, checks their pitch/yaw predicates and exact endpoint order, and retains rejection checks for decreasing distance/score bounds and malformed degree bounds.

Evidence remains outside Git under `/root/pumpkin-parity-lab/artifacts/christine-decreasing-*`. The revised baseline ran twice: vanilla passed all 40 positive assertions, while Pumpkin rejected all 30 wrapped-range commands and failed 16 selection-count assertions. The report conservatively labels parser failures unsupported (`confirmed_mismatch=false`); raw command replies and the failing Rust regression establish the source defect. A preliminary numeric-text oracle also exposed pre-existing SNBT rendering drift (`175f` versus vanilla `175.0f`); that report is retained. The bounded comparison uses NBT predicate counts to verify actual rotation values instead of comparing that unrelated rendering behavior.

No current-source RCON, connected-player, client rendering, or complete parity claim. This patch concerns command parsing and marker selection only.

The new regression failed on the unchanged parser with `argument.range.swapped`. Source commit `0afc2487a9f720812faf16949fa9ec387c2e8fc6` passed these checks under the shared build lock, one build job, disabled debug info/incremental compilation, and the required systemd resource limits:

- `cargo test --locked -p pumpkin-command --lib`: 81 passed.
- `cargo test --locked -p pumpkin-core --lib`: 445 passed, including the regression.
- `cargo fmt --all -- --check`: passed.
- `cargo clippy --locked -p pumpkin-command --all-targets --all-features` and the corresponding `pumpkin-core` command: passed; only the existing `proc-macro-error2` future compatibility warning.
- `cargo build --locked -p pumpkin`: passed.

Binary SHA-256: `7abc98cb7dff57b2d06a90b834b3093ab02f4ada6954180228fc8efcb0618e90`. The first verification scope ended without any check results; its log is preserved separately. The detached restarted scope completed all six checks successfully. The post-fix comparison passed all 80 assertions: 20 per target in each of two trials, no differences, command failures, infrastructure errors or flakes. The baseline and patched scenario snapshots are byte-identical. Coverage uses marker yaw/pitch pairs `(175,85)`, `(-175,-85)`, `(0,0)`, `(170,80)` and `(-170,-80)` with positive NBT fixture checks, `y_rotation=170..-170`, `x_rotation=80..-80` and `x_rotation=170..-170`. This verifies wrapped inclusion, middle-angle exclusion and both inclusive endpoints; pitch stays within vanilla's supported entity range. Both Pumpkin scratch servers stopped normally with no ERROR/panic log lines. Vanilla uses the existing lab reference through RCON; patched Pumpkin uses isolated scratch consoles under the shared engine lock.

Reports: `artifacts/christine-decreasing-baseline/20261016T072151.430479Z-4530378c/report.json` and `artifacts/christine-decreasing-fixed/20261016T073601.668132Z-d1925e2a/report.json`. Check commands/results and binary provenance: `artifacts/christine-decreasing-rust-validation.json`. Final upstream overlap recheck found no equivalent rotation-range fix; selector permission PR4069 concerns another behavior. No upstream messages or PRs were created.
