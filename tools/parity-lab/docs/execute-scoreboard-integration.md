# Execute and scoreboard integration notes

This lane owns the catalog and infrastructure. Changes to execute command
registration, result callbacks and RCON belong to the engine lane. No edits were
made to those source files.

Current upstream master was verified with `git ls-remote upstream
refs/heads/master` at `5b53f064af8708ba33fcaa533b81ca29a53a3310` on
2026-10-15. The released RCON candidate is older. Its failures are not evidence
of independent defects in current source. The existing current-source binary
was used explicitly through the engine's scratch-console transport.

Eight scenarios, two trials each, initially produced four passes, four
differences, no infrastructure errors. The raw report is
`artifacts/runs/20261015T215028.055671Z-fc365a33/report.json`.
The arithmetic overflow, missing operation source, and condition-chain cases
passed. Store signed result, store success and store operation result were
unsupported. Score selection also differed; it was isolated separately because
the original terminal entity-condition probes are themselves unsupported on
this revision. The final catalog uses a mutation counter to observe that case.

`execute store` has an existing upstream issue
[#3758](https://github.com/Pumpkin-MC/Pumpkin/issues/3758) and open fix
[#3987](https://github.com/Pumpkin-MC/Pumpkin/pull/3987). No duplicate fix or
upstream message was created. The overlap search is retained in
`artifacts/jaron-execution-upstream-overlap.json`.

`execute-store-success` intentionally executes a false terminal condition to
prove that a previous sentinel is overwritten with zero. Vanilla reports
`Test failed` for that command, then its positive state assertion passes. The
engine conservatively retains that command failure. Do not suppress the
response or interpret this case's verdict as a clean supported-command pass.

The bounded current-source comparison is console coverage, not RCON coverage.
The 22-case reference run validates command-state expectations; it does not
prove real-client, elapsed-tick, or broad command parity. No permanent service
was replaced during this campaign.
