# Selector rotation axes

The Christine campaign branch merged authorized fork master
`65bca3f7f36af3b4f5e32ac24ed9abd71c930844` without rewriting history. All five
previous Rust source fixes are ancestors of the merge.

The selector parser previously associated x rotation with yaw and y rotation
with pitch. Source commit `9a3a5f9d6acf17a5df63b90d39510a75bb6c42d4`
corrects those assignments to pitch and yaw respectively. The only production
caller changed is selector finalization after parsing; option storage, entity
angle reads and inclusive range evaluation keep their existing behavior.
The existing indexed current-source comparison in `docs/findings.md` establishes
that a marker with `Rotation:[90.0f,20.0f]` has yaw 90 and pitch 20. Vanilla
selects it with `y_rotation=80..100` and `x_rotation=10..30`, while upstream
selects it with the swapped ranges. Both trials agree; entity and indexed NBT
controls pass. Evidence remains in the live lab at
`artifacts/jaron-findings-indexed-upstream/20261016T022750.407251Z-8c88b84f/report.json`.

Official vanilla 26.3 was inspected locally with Vineflower 1.12.0.
`EntitySelectorOptions` stores x/y in rotX/rotY; the parser's
`finalizePredicates` binds those to `Entity.getXRot`/`Entity.getYRot`.
`createRotationPredicate` wraps both endpoints and the entity angle, then uses
inclusive comparisons with an OR across the signed boundary. Decompiled Java
and binary inspection output remain outside the repository.

Read-only upstream searches on 2026-10-16 found only original closed PR #1925
for x_rotation/y_rotation. Open selector PRs #4069 (permissions), #3795 and
#3582 do not change these axis assignments. No external patch was integrated.
Upstream master was `5b53f064af8708ba33fcaa533b81ca29a53a3310`.

Both new Rust parser regressions fail on the unchanged source, while the
existing namespace parser test passes (Cargo exit 101). The log and exact
command are retained in `artifacts/christine-rotation-red.{log,json}`. An earlier
interrupted build produced no test result and is not counted as validation.

Wrapped-range validation uses increasing endpoints (`170..190`, `350..370`)
that cross the signed-angle or zero boundary after wrapping. The shared
`FloatDegreeBounds` parser separately rejects decreasing endpoints such as
`170..-170`; this patch does not change that existing limitation.

Fixed-source Rust validation passed:

- `cargo fmt --all -- --check`.
- `cargo test --locked -p pumpkin-core --lib`: all 440 tests passed, including
  the two regressions.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`.
- `cargo build --locked -p pumpkin`, including the dependent binary/host crates.

All Cargo operations used the shared target and build lock, one build job,
disabled debug information/incremental compilation, and a systemd scope capped
at 5 GiB memory, no swap, and 200% CPU. Only the existing `proc-macro-error2`
dependency future-compatibility warning was reported. Commands, exit codes and
timestamps are in `artifacts/christine-rotation-rust-validation.json`; individual
logs use `artifacts/christine-rotation-{fmt,tests,clippy,build}.log`.

The immutable binary built from the source commit above has SHA-256
`82748f9304014ce4f7cdfd67fc33684c9fd9ace0d2fd8f896c1de82edc41e0fb`.

The focused live vanilla/patched comparison passes all 20 observations on each
target in each of two trials (80 positive assertions total), with no differences,
infrastructure errors or flakes. It verifies yaw 90/pitch 20 against independent
and swapped axis filters, signed-boundary and zero-crossing ranges, equivalent
angles above 360 degrees, and inclusive endpoints. Scratch marker fixtures use
yaw/pitch pairs (-175, 5), (90, -5), (170, 10), and (-170, -10). Indexed rotation
reads are retained as raw controls. Both scratch server logs show successful
startup and shutdown with no ERROR or panic lines. Evidence:
`artifacts/christine-rotation-live/20261016T071335.333428Z-9533a764/report.json`
and `artifacts/christine-rotation-live-validation.json` in the live lab.

The comparison used the existing engine lock and bounded console arena; no lab
infrastructure or permanent catalog cases were added. The existing released
candidate service was not used to validate the source patch. No real-client or
visual gameplay validation is claimed. Final upstream overlap searches still
find no open x_rotation/y_rotation fix.
