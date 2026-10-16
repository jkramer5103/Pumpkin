# Catalog audit handoff to the engine owner

No `lab/` files were edited in this audit. All 100 reference cases meet their
positive expectations twice; raw evidence is in
`artifacts/jaron-audit-vanilla-final.json`. The engine's alternating-order run
also has 244/244 passing vanilla observation steps:
`artifacts/jaron-audit-release/20261016T023515.296739Z-3e51e1f6/report.json`.

Two intentional vanilla failures remain visible in each trial:

* `keep-occupied`: setup's occupied `setblock ... keep` returns failure, while
  the positive final probe confirms the original stone survives.
* `execute-store-success`: the false terminal condition reports failure, while
  the final probe verifies that success zero replaced the sentinel.

These are valid reference experiments, not invalid probes to delete. The schema
has no expected-failure declaration; consider a narrow explicit declaration
with engine verification if successful parity classification of such cases is
needed. Do not suppress generic failure text or loosen observations. Normal
overlap rejection is another intended-negative catalog behavior, although the
current classifier did not flag its vanilla response in this run.

The new prepend, negative-index insertion and copied-list independence cases
use `execute store result ... data get` to prove list length and every index.
This is intentionally stronger than unordered NBT subset matching and remains
blocked on the checked current source's missing execute-store support. Source
console evidence is separate from full RCON coverage. Optional prerequisite
metadata would make this limitation clearer without silently skipping it.

The independent authoring reader now delegates to the engine's strict JSON
reader, so duplicate keys cannot overwrite an earlier field silently. Recursive
catalog validation checks cross-directory IDs/sequences, but does not change
the engine's default nonrecursive execution scope or inflate coverage counts.
