# Entity score selectors use existing score holders

A bounded live vanilla/current-upstream comparison confirmed a defect in
`EntitySelectorPredicate::Scores`. Scores written to real marker entities failed
to match nonzero selector filters, while entities without a score matched zero.
The old code used display/type names and indexed the scoreboard's
objective-to-holder map in the reverse order, then defaulted missing values to
zero.

The fix uses `EntityBase::get_scoreboard_name()` and the scoreboard's existing
read-only `get_score_value(holder, objective)` API. Every requested objective and
score must exist and satisfy its bounds. An empty score filter remains
unconstrained. No score is created by selection. Name/team predicates and
execute command registration are outside this patch.

Vanilla 26.3 was checked through the decompiled `EntitySelectorOptions` score
predicate and the `Scoreboard.getPlayerScoreInfo` / `Entity.getScoreboardName`
call chain. Nonplayer entities use UUID score-holder names. Decompiled material
and bytecode inspection output remain outside Git. Open upstream searches found
no identical selector-score fix; results are retained in
`artifacts/jaron-execution-upstream-overlap.json`. The separate execute-store gap
already has upstream issue #3758 and PR #3987.

Validation completed under the shared Cargo lock with one job, disabled debug
info/incremental compilation, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%:

- Both new score-filter regression tests failed before the fix (exit 101,
  `artifacts/jaron-score-red.log`). The original helper extraction preserved the
  old lookup/default behavior for that failing run.
- `cargo test --locked -p pumpkin-core --lib`: **437 passed**.
- `cargo fmt --all -- --check`: passed.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`: passed.
- `cargo build --locked -p pumpkin`: passed.
- `artifacts/jaron-score-verify-build.json` and
  `artifacts/jaron-score-verify-final.{json,log}` preserve commands and exit codes.
  An initial formatting failure is retained separately and is not a passing
  result.

The final live report is
`artifacts/jaron-score-selector-20261016T014347.031399Z/report.json`.
Vanilla and the fixed binary each passed **24/24 checks**, twelve controls
repeated twice. Current upstream consistently failed missing-score exclusion,
nonzero UUID-backed score selection, populated-score zero rejection,
multiple-objective matching, nonexistent-objective exclusion and reset-score
exclusion. Fixture counts, explicit-zero and empty-filter controls passed.
The comparison held the engine's shared process lock and used one scratch
source server at a time. Console logs and raw responses were retained.

Current upstream master was reverified at
`5b53f064af8708ba33fcaa533b81ca29a53a3310`. The patched binary SHA-256 is
`60ba601ed958d4d71f8c5265a07743e115cd01d2883ebc0157040df38d335548`.
Its scratch-console checks do not establish RCON support. No permanent service
was replaced. Connected-player behavior, client visuals, full workspace tests
and full current-source RCON catalog coverage remain untested.
