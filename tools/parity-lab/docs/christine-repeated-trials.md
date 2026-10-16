# Repeated trials and tick control, 2026-10-15

Lab execution now repeats the whole selected suite, alternating sorted and reverse
order by default. Seeded shuffle records the full schedule without changing global
random state. Optional declared resets run before each target/trial. Pending trial
series cannot carry a passing or confirmed-mismatch verdict. Additive report fields
describe outcome counts, target variability, isolation limits and tick capabilities;
existing dashboard keys remain intact.

Two stateful regression tests fail against the original runner: leaked state was
hidden by consecutive per-scenario repeats, and a scenario retained a pass when a
later scenario interrupted before its second trial. Both pass with the changes.
The reset variant removes the fixture's order dependency. Fixtures demonstrate
flakiness detection; the bounded live runs below did not exhibit flakes.

Validation: `python3 -m unittest discover -s tests -p 'test_core*.py' -q` passes
69 tests. `python3 ops/publish-lab.py --message 'fix(parity): isolate repeated trials
and verify tick capabilities'` independently passes 88 full-suite tests and pushes
`parity-lab` at `2e416592a6a8d710f3442d0893f9af8d53d98325`. The serialized
publisher had already integrated the implementation in `b4f788585ff543c1127e5abbb92ac70046ea0bd7`
and the final tick-acknowledgment test in `065f7ec2354a1f2dead18ad658b1cc5d92d0b1e4`.
No shared live-repository commit was made.

## Actual live comparisons

Upstream master was rechecked with `git ls-remote upstream refs/heads/master`:
`5b53f064af8708ba33fcaa533b81ca29a53a3310`. Existing immutable debug binaries
were reused; no cargo build or service replacement was needed. Every mutation,
including scratch-server startup/shutdown and tick-state restoration, held the
engine's shared file lock. Source comparisons ran in systemd scopes capped at
MemoryMax=3G, MemorySwapMax=0 and CPUQuota=150%.

| Candidate | Trials | Anchor | Arithmetic | Confirmed mismatches | Flakes |
| --- | --- | --- | --- | --- | --- |
| Current upstream, scratch console | 2 | differs twice | passes twice | 1 | 0 |
| Existing source fix f123eb8, scratch console | 2 | passes twice | passes twice | 0 | 0 |
| Restored released candidate, RCON | 2 | not selected | rejected syntax twice | 0 | 0 |

The source run order was anchor, arithmetic, arithmetic, anchor. Vanilla's two
anchor observations are `Test passed` / `Test passed`; unchanged upstream returns
`Test passed` / `Test failed` on both trials. The existing fix returns both passes.
This reconfirms the previously fixed anchor defect; no new Pumpkin source defect
is claimed. Released Pumpkin rejects the `#trial` score-holder commands and terminal
score predicate; raw syntax rejection remains unsupported, not a confirmed defect.

The standalone tick probe succeeds on vanilla RCON, released Pumpkin RCON, current
upstream console and fixed console: freeze, step one, observe gametime advance by
exactly one, restore running state. An acknowledgment without advancing game time
fails a targeted fixture test. This verifies tick control, not random-seed,
entity-order, client gameplay or general simulation determinism. Current upstream
still has no RCON transport; console success does not establish RCON readiness.
Scratch worlds use generated seeds and are fresh per attempt; vanilla retains its
configured world. Declared resets do not prove arbitrary world restoration.

The source command was executed once with each immutable source binary:

```sh
python3 -m lab run --targets runtime/targets.json \
  --scenarios artifacts/christine-repeated-scenarios --repeat 2 \
  --reset lab/examples/positioned-anchor-reset.json --order alternating \
  --probe-ticks --pumpkin-console /absolute/path/to/immutable/binary \
  --output artifacts/repeated-upstream
```

The input directory contains unchanged copies of `lab/examples/positioned-anchor.json`
and `lab/examples/scoreboard-trials.json`. Upstream exits 1, fixed exits 0. Released
RCON was checked with the same directory, `--id scoreboard-trials --repeat 2
--probe-ticks --output artifacts/repeated-release`, without console/reset options;
it exits 1. No existing scenario or expectation was removed or weakened.

Local evidence is preserved outside Git:

- `artifacts/repeated-upstream/20261015T214449.674865Z-6175cf63/report.json`
- `artifacts/repeated-fixed/20261015T214536.841659Z-7a9506c4/report.json`
- `artifacts/repeated-release/20261015T214605.321901Z-29b8ef8d/report.json`
- `artifacts/christine-repeated-validation.json` records report audits and binary hashes.
- `artifacts/christine-repeated-regression-before.log` preserves both original-runner failures.
- `artifacts/christine-repeated-core-tests.log` and `artifacts/christine-repeated-publish.log`.

All scratch processes stopped cleanly. Logs contain expected debug/development and
fresh-world warnings, with no ERROR/panic lines. Rust tests were not rerun because
this change modifies Python tooling only. No new source build, client or performance
validation is claimed.
