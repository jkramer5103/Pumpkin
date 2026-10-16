# Catalog coverage and evidence

Audit date: 2026-10-16. This is a command-observable differential lab for Java
26.3. The default catalog contains **100 distinct scenarios and 122 positive
observation steps**, not 100 confirmed Pumpkin defects or 100 gameplay tests.
No renamed duplicate experiment was found or removed. Material-filter cases,
state-filter cases, negative controls and operator boundaries test different
rules even when they share a fixture.

`scenarios/` is deliberately nonrecursive in the engine. Four focused findings
replays in `scenarios/findings/` and one verified-tick case in
`scenarios/simulation/` are opt-in. Recursive validation finds 105 definitions,
but the four findings replays overlap existing default cases and are not extra
independent coverage. The water case adds one bounded simulation behavior.
The separate anchor shrink reproducer and generated fuzz sequences are also
excluded from the default count.

## Command behavior

| Area | Default cases | What is observed | Important limit |
| --- | ---: | --- | --- |
| Blocks | 5 | Placement, replacement, keep in air/occupied cells, clearing old container data | Immediate state; drops and player actions untested |
| Block states | 5 | Log/pillar axes, stairs, waterlogged slab, placement NBT | Command placement, not neighbor updates or rendering |
| Block predicates | 4 | Partial properties, tags, tag/property intersection, negative gating | Rejected syntax stays visible |
| Fill | 9 | Bounds, reversed endpoints, shell/interior modes, material/state/tag filters | Small cuboids only; no performance or large-world claim |
| Clone | 9 | Air/masked/material/state selection, move, overlap modes, container data | Command copy semantics; ticking behavior after copy untested |
| Entities/selectors | 18 | Tags, bounded kills, position, distance/box limits, sort/limit, names, rotation | Markers; no real players or mob AI |
| Entity NBT | 14 | Summon/merge/remove, typed/list subset matching, indexed replacement/removal, append/prepend/insert/copy | Custom marker data; not inventories or full entity serialization |
| Entity effects | 2 | Stored duration/amplifier/visibility and selective clearing | Frozen armor stand; expiration and player effect behavior untested |
| Scoreboard | 26 | Arithmetic/wrap/floor rules, comparisons/ranges, holder identity/absence, objective/reset lifecycle | Dummy objectives and marker/fake holders; no display/client claim |
| Execute | 8 | Relative origin, conditions, self scores, result/success stores | Known missing store/terminal-condition support blocks some source checks |
| **Total** | **100** | **122 positive observation steps** | These are experiments, not counts of independent bugs |

The four final additions test prepend order, negative insertion index, independence
of an NBT list copied with `set from`, and reset across all objectives. Initial
values are positively checked. List length and every resulting index are read
numerically through sentinels, because NBT selector list patterns are unordered
subsets. The integer teleport case now combines its original Pos-content check
with a tight spatial predicate: the content check alone could accept permuted
coordinates. No previous failing evidence or assertions were removed.

## Simulation and actual gameplay

`scheduled-water-down` uses freeze/step and verified game-time barriers to check
initial source/air, air at tick four, water at tick five and persistence at tick
six. Two trials on clean upstream show the one-tick delay; the existing scheduler
patch passes both trials. This is real bounded server simulation, but asserts
only block material. See [simulation evidence](simulation.md).

**No connected-client gameplay has been tested.** There is no movement, collision,
inventory, crafting, combat, player interaction, UI, visual, packet-stream or
multi-client synchronization coverage. Summoned marker and armor-stand command
checks do not establish these behaviors. Falling sand and lamp timing have
vanilla-only evidence, with Pumpkin checks blocked by chunk residency or state
syntax; neither is promoted into the passing catalog. Random growth, long-delay
scheduling, complete fluid properties and large redstone networks are untested.

## Protocol and engine checks

Real RCON commands exercise authentication and command/response transport against
both installed targets. Fake TCP fixtures in `tests/test_core_rcon.py` and
`tests/test_core_integration.py` separately test fragmented headers/bodies,
multi-packet replies and fences, split UTF-8, malformed sizes/types/IDs,
timeouts, authentication rejection, disconnection, and bounded response memory.
The independent probe has its own fragmentation/multi-frame fixture. These are
RCON tests, not Minecraft login, status, encryption, compression or play-protocol
tests. Actual adversarial transport faults were not injected into the live servers.

Engine tests cover lock serialization, setup/cleanup after failures, explicit
positive expectations, interrupted evidence, repeated order/reset policies,
conservative unsupported/flaky classifications, verified ticks, shrink/replay
and finite seeded fuzz generation. Passing fake fixtures prove those paths in
the lab, not Pumpkin's implementation of the modeled behavior.

## Baselines and validation

The permanent candidate is the pinned release `0.2.0+26.3-26.51` (source tag
`204a94ed895f041a845630d5a23c094705a0704e`). Current upstream master was rechecked
with `git ls-remote` at `5b53f064af8708ba33fcaa533b81ca29a53a3310` during this
audit. Its previously built binary has SHA-256
`463905ffe45d2dd55d1cf6511bdd7548fd21ef8977125bfe57b7a2ea55350eb7`.
That source has no RCON implementation, so current-source comparisons use the
explicit scratch-console transport. The attempted source deployment was rolled
back to the release under the engine lock; see [server records](servers.md).
A released-candidate rejection is not evidence of a new current-source bug.

Validation commands:

```sh
python3 -m infra.catalog
python3 -m infra.catalog --recursive
python3 -m lab list --scenarios scenarios
python3 -m unittest discover -s tests -p 'test_scenarios*.py' -v
python3 -m unittest discover -s tests -q
python3 infra/validate_scenarios.py --target vanilla --repeat 2 \
  --output artifacts/jaron-audit-vanilla-final.json
python3 -m lab run --targets runtime/targets.json --scenarios scenarios \
  --repeat 2 --timeout 3 --lock-timeout 30 --probe-ticks \
  --output artifacts/jaron-audit-release
```

The independent final vanilla run passed **200/200 expectation sets** (two per
scenario), retaining every raw setup, mutation, observation and cleanup response.
This validates the reference expectations, not cross-server parity. The engine
run uses alternating whole-catalog forward/reverse order and keeps per-target
variability visible. Both runners use the same shared file lock. Final report
paths, exit codes and result classifications are recorded in
`artifacts/jaron-audit-validation.json`; local raw evidence is intentionally
excluded from publication.

The final released-candidate engine run completed all 200 paired attempts:
**0 pass, 24 stable unsupported, 76 infrastructure-error scenarios**, zero
confirmed mismatches and zero detected flaky scenarios. Vanilla passed all
244 observation steps; the released Pumpkin passed zero, with unsupported
commands and unloaded-world errors retained. This is blocked coverage, not
100 newly discovered defects. A five-case source subset is recorded separately;
an initial attempt timed out waiting for the shared lock before any connection.

The completed current-source retry ran each of five cases twice, with no
infrastructure errors or detected flakes: `score-reset-all-objectives` passed;
the three new list cases remained unsupported because execute store is missing,
and the strengthened teleport probe remained unsupported because its terminal
entity condition is rejected. Vanilla passed all 20 subset observations,
Pumpkin passed the four reset observations, and no new mismatch was confirmed.
The full Python suite passed **109 tests**, including **26** assigned catalog
and infrastructure tests. The initial lock-timeout report remains separate
from the complete retry.

The focused five-family upstream/fixed replay from the preceding campaign is
preserved in `artifacts/jaron-findings-validation.json`: vanilla passed 46/46
observations, clean upstream had five confirmed differences, and the existing
combined Jaron patches passed four families with rotation still failing. These
are bounded console checks, not a full current-source RCON catalog. The separate
Christine positioned-anchor fix has its own live baseline/fixed evidence.
See [confirmed findings](findings.md) and [execute coverage](execute-scoreboard-catalog.md).

## Flakiness and remaining gaps

A stable unsupported command, a failed reference expectation and an unloaded
world are separate from a confirmed behavior mismatch. Two equal errors cannot
pass a positive observation. Flaky repeats are retained and excluded from
confirmed-mismatch counts; no absence-of-flakiness claim extends beyond the
specific recorded runs.

Known sources of uncertainty are source scratch chunk residency during longer
simulations, unsupported state/store/terminal-condition syntax, incomplete reset
coverage outside the declared arena, and command result text. Intentional
negative operations (occupied keep, rejected normal-overlap clone, false stored
success) can be reported as command failures even when their final state is
correct. The schema has no expected-failure or prerequisite declaration, so
those engine classifications need review; observations must not be weakened to
make them green. No test claims arbitrary world snapshot restoration.

There is no full current-source catalog result, real-player coverage, complete
save/reload world-state verification, or performance/load testing. Existing source
patches have the targeted Rust/live evidence described in their finding documents;
this final catalog audit made no new Rust changes or builds.
