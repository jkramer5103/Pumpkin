# Fill state filter investigation

Baseline: current upstream `5b53f064af8708ba33fcaa533b81ca29a53a3310`.
The original `BlockPredicate::test` accepts only a block material, and `/fill`
passes it `current_block`; parsed state constraints never reach matching.

Vanilla 26.3 was checked using its verified official server and locally decompiled
`BlockPredicateArgument.BlockPredicate.test` / `TagPredicate.test`. The named-block
predicate compares only specified properties. Tag predicates require each property
to exist, have a valid value, and match the actual state. Unspecified properties
remain unconstrained. Generated Pumpkin block properties can supply actual values
without hardcoding state IDs or property tables.

Live vanilla evidence: place a default oak log at `0 64 0`; fill that cell with
gold replacing `oak_log[axis=x]`; vanilla reports `No blocks were filled`, and
`execute if block 0 64 0 oak_log[axis=y]` returns `Test passed`. Raw replies remain
in the private artifact `jaron-vanilla-fill-nonmatch.json`.

Validation: the regression failed with original material-only matching: a default
axis=y oak log incorrectly matched `oak_log[axis=x]` (red3 exit 101). After the
fix, `cargo test --locked -p pumpkin-command` passed **81 unit tests and 5 doc
tests** (green exit 0). Cases cover named and tag properties, nonmembers, missing
and invalid tag properties, unconstrained properties, and partial stair predicates.
The first invocation ended during compilation and the second hit a corrected
borrow in the test fixture; neither is counted as a behavioral red result.

The patch adds `BlockPredicate::test_state` using generated actual-state properties
and switches fill to pass the actual state ID. NBT matching is explicitly outside
this helper. `cargo fmt --all -- --check` and command-crate clippy (all targets/features)
passed. The full patched binary built successfully in 2m42s after rebuilding the
relevant command package: an initial build had reused stale shared command metadata and failed to find the new method. All Cargo operations held
the shared lock and required resource caps. No unrelated cache was removed.

The immutable patched binary is tied to source commit
`701809df211b0dcfa6996595f99ff7327cad8d78`, SHA-256
`4e4242a9e39704e241c95a7d7d65c2487377edbe5d6b75c4528ba7f86df27fd3`.
Console probes use the engine lock and a separate 3 GiB/150% CPU scope. Current
upstream reproduced the state-filter bug twice for named and tag filters against
vanilla, with positive initial-state and negative branch controls. The patched binary then matched vanilla on all checks in both repeats for both
named and tag filters. Each attempt positively observed initial state, checked
that a deliberately false block branch stayed false, verified preservation under
an x-axis filter, and verified replacement under a matching y-axis filter. Current
upstream failed preservation in all four attempts. This establishes one state
filter defect through two filter forms, not four separate bugs.

Raw report: `artifacts/jaron-fill-console-20261015T212702.924070Z/report.json`.
The first loader attempt hit an embedded GameTest palette schema error (`Name`
missing). A private original one-block loader fixture using the parser's supported
schema made one scratch chunk writable. This is setup, not a GameTest parity pass;
no embedded asset or source test was modified. The next attempt retained a relative
binary-path setup error. Both earlier reports/logs remain preserved. Scratch flat
terrain places the small loader and all mutations inside the bounded arena.

Clean upstream built in 9m39s and booted as the lab candidate. This revision has
no RCON implementation/configuration, so source-baseline RCON comparison is
unavailable. The released candidate/configuration was restored under the engine
lock and RCON/gamerules verified. Old-binary responses do not validate this patch.
NBT filtering, placement state parsing, clone state filters, chunk loading, and
execute predicate support remain separate gaps. No engine-lane files are edited.

Overlap review: existing issue #2592 documents related command/loading gaps;
PR #3827 adds setblock state parsing, and PR #3964 adds fill callbacks. Neither
change is incorporated here. No upstream PR, issue or comment was posted.

Before any future upstream submission, the human author must join with a real
client and verify that an x-log-only fill changes the horizontal log while a
vertical log remains, then repeat with a logs tag filter across two log types.
Capture the before/after blocks in a screenshot or recording and attach it to
any human-opened PR. Capture: <attach screenshot or recording here>.
