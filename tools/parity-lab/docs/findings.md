# Five confirmed current-source differences

This audit follows five behavior families with repeatable live evidence, rather
than ranking old-release error counts. Upstream master was rechecked with
`git ls-remote upstream refs/heads/master` on 2026-10-16 and remains
`5b53f064af8708ba33fcaa533b81ca29a53a3310`. The existing immutable binary for
that commit was used; **no Rust build or Cargo operation ran in this audit**.
Vanilla is the verified official Java 26.3 server.

The replay fixtures are under `scenarios/findings/`, outside the default catalog.
They adapt existing cases to supported command observations, not additional
coverage counts. The fifth fixture is the existing
`scenarios/simulation/scheduled-water-down.json`.

| Finding | Vanilla expected behavior | Current upstream actual behavior | Fork status |
| --- | --- | --- | --- |
| Fill state constraints | Default vertical oak log survives `replace oak_log[axis=x]`; matching y filter replaces it | x filter replaces the vertical log | Previously fixed in `701809df211b0dcfa6996595f99ff7327cad8d78` |
| Selector NBT lists | Empty pattern rejects a populated list; pattern longer than actual list rejects; inversion agrees | Empty and oversized patterns match; inverted empty pattern rejects | Previously fixed in `31a781da7ec52a274bc8104a6875508f832e7055` |
| Entity score selectors | Absent score does not match zero; UUID-backed score seven matches seven | Absent score matches zero; assigned seven does not match seven | Previously fixed in `448733d30ae716958dadf9ec12c2ffa8a8496f1f` |
| Scheduled fluid boundary | Air below source through tick four, downward water on tick five | Air remains on tick five; water arrives on tick six | Previously fixed in `94b5a5248ac4e59dda519f5c7ef958cf9a71f90d` |
| Rotation selector axes | `y_rotation` reads yaw, `x_rotation` reads pitch | `x_rotation` reads yaw, `y_rotation` reads pitch | Confirmed and unpatched; no Rust validation attempted here |

## Reproduction and evidence

Use the live lab root. This bounded launcher always repeats twice, uses the
engine's shared file lock, and explicitly starts private Pumpkin consoles with
a loaded arena. It calls the existing runner, preserving raw responses,
scenario copies, tick barriers, errors and completion state. The permanent
vanilla target uses RCON. Source Pumpkin uses **scratch console, not RCON**.

```sh
systemd-run --scope --unit=pumpkin-parity-findings-replay \
  -p MemoryMax=3G -p MemorySwapMax=0 -p CPUQuota=150% \
  python3 infra/validate_findings.py \
  --pumpkin-console runtime/downloads/pumpkin-source-5b53f064af8708ba33fcaa533b81ca29a53a3310 \
  --output artifacts/findings-replay
```

To replay one finding, append one of these options to that command:

| Finding | Replay option |
| --- | --- |
| Fill | `--id findings-fill-properties` |
| NBT | `--id findings-nbt-lists` |
| Scores | `--id findings-score-holders` |
| Fluid | `--id scheduled-water-down` |
| Rotation | `--id findings-rotation-axes` |

Exit 1 is expected when differences reproduce; exit 2 means infrastructure or
validation failed. A failed systemd unit with `ExecMainStatus=1` therefore needs
its report inspected rather than being treated as a crashed server.

The baseline binary SHA-256 is
`463905ffe45d2dd55d1cf6511bdd7548fd21ef8977125bfe57b7a2ea55350eb7`.
The previously built fork binary is
`runtime/downloads/pumpkin-jaron-scheduled-ticks-fixed`, tied to source commit
`94b5a5248ac4e59dda519f5c7ef958cf9a71f90d`, SHA-256
`cb10cb0da524952db4d141b7d8ed00538f01c2a8d3f815e09f03d3e1c0313b02`.
Substitute that binary path to check the accumulated fixes. The launcher records
the actual binary digest in `binary.json`; source provenance comes from the
existing build record `artifacts/jaron-simulation-verify-build.json`.

The final current-upstream run is
`artifacts/jaron-findings-indexed-upstream/20261016T022750.407251Z-8c88b84f/report.json`:
**five confirmed differences, zero errors, zero flakes**, two trials each.
Vanilla passed 46/46 observations; upstream passed 24/46, with exactly the
finding-specific checks failing consistently. The accumulated fork run is
`artifacts/jaron-findings-indexed-fixed/20261016T022939.618827Z-66486fd8/report.json`:
**four passing families and the rotation difference**, zero errors or flakes.
Vanilla passed 46/46; the fork passed 38/46. These are replay results for existing
patches, not newly built fixes.

Both final reports have complete attempts, no unsupported commands, correct
indexed rotation values, and verified six-tick water trials. All 22 scratch
console logs lack ERROR/panic lines. Earlier complete replays remain under
`artifacts/jaron-findings-upstream/` and `artifacts/jaron-findings-fixed/`.
The evidence assertions are recorded in `artifacts/jaron-findings-validation.json`.
Assigned Python tests passed 24/24; the full suite passed 107/107. Commands:
`python3 -m unittest discover -s tests -p 'test_scenarios*.py' -q` and
`python3 -m unittest discover -s tests -q`. The default catalog still validates
96 distinct scenarios; no original tests were removed or weakened.

Scratch console logs remain in their run directories. Runtime evidence is
private and excluded from Git publication.

## Fill: parsed properties never reached matching

Replay creates default oak and birch logs beside stone, avoiding the separate
unsupported state-placement syntax. It checks all initial materials and an
intentionally false diamond branch, then checks preservation after the x filter
and replacement after the y filter. Only preservation fails on upstream, twice.
Vanilla's expected `No blocks were filled` response from the nonmatching filter
is retained; observation scores establish the resulting block state separately.

At the pinned upstream revision,
[`BlockPredicate::test`](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-command/src/argument_types/block_predicate.rs#L46)
accepts only a block material and ignores parsed properties.
[`fill.rs`](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-core/src/command/commands/fill.rs#L136)
reduces the actual state to that material before calling the filter. The existing
fork fix passes the actual state to generated property matching. NBT filtering
and placement parsing remain separate. See [the detailed investigation](fill-state-filters.md).

Read-only overlap review found related issue
[#2592](https://github.com/Pumpkin-MC/Pumpkin/issues/2592) and open
[PR #3827](https://github.com/Pumpkin-MC/Pumpkin/pull/3827). The latter changes
setblock property parsing, not fill predicate matching; its file diff was read.
No claim is made that the broader command/loading gaps are newly discovered.

## NBT: empty and oversized selector list patterns

The marker has exactly `Tags:["pp_find","fixture"]`. Entity existence and the
nonempty subset both pass. Empty and three-element repeated patterns must
reject that two-element list; the inverted empty pattern must accept it. All
three discriminating checks fail twice on upstream.

The pinned
[`matches_nbt` list arm](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-core/src/command/argument_types/entity_selector/mod.rs#L434)
checks each pattern value against any actual value without an empty-list or
size guard. The prior source fix adds those guards, preserving unordered subset
matching. This is one list-matching family, not three independent bugs. See
[entity evidence and previous Rust validation](entities-selectors.md).

Open [PR #4003](https://github.com/Pumpkin-MC/Pumpkin/pull/4003) bounds SNBT parser
depth, not selector matching. Closed
[PR #3726](https://github.com/Pumpkin-MC/Pumpkin/pull/3726) describes a similar
size guard in the separate `nbt_path.rs` comparator. It is related prior work,
not evidence that the selector comparator is already corrected. No change from
either PR was integrated by this audit.

## Scores: missing values and holder identity

One marker is positively counted before filtering. An absent score incorrectly
matches zero. After `scoreboard players set <marker-selector> pp_find 7`, the
marker incorrectly fails the seven filter. A fake holder named `marker` with 99
remains an explicit non-alias control; that particular check passes upstream.

The upstream
[`Scores` predicate](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-core/src/command/argument_types/entity_selector/mod.rs#L536)
uses `entity_actual_name`, indexes the objective-first score map by holder, and
substitutes zero for absent values. The existing fork fix uses the canonical
score-holder name and existing read-only lookup. See
[the score-holder investigation](score-selector-score-holders.md).

Closed [PR #3595](https://github.com/Pumpkin-MC/Pumpkin/pull/3595) documents
scoreboard commands using canonical entity holders;
[PR #3596](https://github.com/Pumpkin-MC/Pumpkin/pull/3596) changes execute score
arguments. Neither describes fixing this selector predicate. The current
open search for selector/score overlap returned no items; this is a bounded
search result, not a guarantee that no related work exists.

## Fluids: the due tick is one step late

The replay verifies initial water/air, air at tick four, water at tick five and
water at tick six using game-time barriers. Each attempt advances exactly six
verified ticks on each engine. Only tick five fails upstream. No elapsed sleep
is used as proof of simulation progress, and fluid level is not asserted.

Upstream
[`ChunkTickScheduler::step_tick`](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-world/src/tick/scheduler.rs#L22)
drains the previous cursor slot, while scheduling uses cursor plus delay. The
prior fork fix collects the advanced slot and synchronizes queue/cursor access.
See [the simulation investigation](simulation.md) for prior failed regressions,
passing Rust validation and separate blocked sand/lamp experiments.

Open [PR #4010](https://github.com/Pumpkin-MC/Pumpkin/pull/4010) extends delays
beyond 255 and handles saved tick tracking. Its current file diff still tests
completion after `delay + 1`; it does not fix this five-versus-six boundary.
Active-chunk gating in [PR #3639](https://github.com/Pumpkin-MC/Pumpkin/pull/3639)
is another concern. No long-delay or unloaded-chunk timing claim is made here.

## Rotation: selector parser swaps yaw and pitch

The marker is summoned with `Rotation:[90.0f,20.0f]`. Indexed `data get entity`
reads independently establish yaw 90 and pitch 20 on both engines. Vanilla
prints `90.0f`/`20.0f`; Pumpkin prints `90f`/`20f`. That scalar formatting difference
is retained as raw control evidence and is not counted as a sixth finding. Selector NBT list matching is unordered, so its subset control
alone would not establish axis order. Entity existence and the NBT-content
control pass. Vanilla counts one for `y_rotation=80..100` and
`x_rotation=10..30`, and zero for the swapped ranges. Upstream returns zero,
zero, one and one respectively, twice. This confirms selection behavior rather
than a summon or numeric-data parsing failure.

[`option.rs`](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-core/src/command/argument_types/entity_selector/option.rs#L231)
stores x/y options in x/y fields. The parser's
[`selector()`](https://github.com/Pumpkin-MC/Pumpkin/blob/5b53f064af8708ba33fcaa533b81ca29a53a3310/crates/pumpkin-core/src/command/argument_types/entity_selector/parser.rs#L147)
then assigns x to `RotationType::Yaw` and y to `RotationType::Pitch`.
`RotationType::value_from_entity` reads the named yaw/pitch field, identifying
the parser assignments as the source of the reversal. This remains unpatched;
no Rust compilation or source regression test was run in this no-build audit.

Read-only searches for `x_rotation` and `y_rotation` each found the original
closed selector [PR #1925](https://github.com/Pumpkin-MC/Pumpkin/pull/1925), whose
description itself assigns x to yaw and y to pitch. Open selector/rotation
matches #3795 and #3582 were inspected at the file-diff level; neither touches
the selector parser. No identical open fix was found in these searches.

## Exclusions and limitations

The previous permanent-release catalog report
`artifacts/jaron-lifecycle-catalog/20261016T021834.246879Z-6afa3c2a/report.json`
contains 23 differences and 73 infrastructure-error scenarios, with zero
confirmed mismatches. Those counts do not establish 96 Pumpkin bugs.
Unsupported terminal entity/block conditions were replaced only in these
focused replays by reset score sentinels and supported terminal score checks.
The original catalog tests and failed evidence are preserved.

A draft added indexed data reads without `limit=1`; both engines rejected the
multi-entity selector. That invalid probe is retained under
`artifacts/jaron-findings-final-upstream/` and is excluded from confirmation.
The corrected replay uses a single-entity selector. Earlier invalid reference
fixtures, unloaded-arena runs and unsupported execute-store cases likewise
remain evidence of their stated limitations, not additional confirmed bugs.

No real-client gameplay, visuals, inventory, combat, full fluid properties,
random growth, or current-source RCON was tested. The original released lab
candidate remains installed because upstream lacks RCON. All scratch processes
are closed by the runner. No issue, PR, comment or message was posted upstream.
Read-only API search responses and inspected PR diffs are retained in
`artifacts/jaron-findings-overlap*.json`; the search is not exhaustive.
