# Entity and selector coverage

The entity campaign adds **23 distinct scenarios**, bringing the catalog from
50 to 73. Live vanilla Java 26.3 satisfied all 23 new scenarios plus the corrected
`tag-intersection` scenario twice: **48/48 expectation sets**, with no rejected
fixture commands. These are immediate command-state checks with simulation frozen.
No connected player, inventory, combat, client rendering or timed effect expiry
was exercised.

The new cases cover summon position precedence; inclusive distance bounds;
negative selection boxes; nearest/furthest ordering before limits; limited
execution counts; quoted names and empty-tag predicates; empty/oversized NBT
lists, compound-list subsets, numeric types and inversion; yaw/pitch and angle
wrapping; nested removal and indexed list mutation; relative/fractional teleport;
spatial cleanup; and effect fields/selective clearing on armor stands.

Every entity is tagged `pp`, summoned inside the shared arena, and cleaned up by
a bounded type/tag selector. The two effect cases inspect `active_effects` on
summoned armor stands with gravity disabled. Vanilla confirms duration 1200 ticks,
amplifier `2b`, and hidden icon/particle fields for a 60-second level-three speed
effect; simulation does not advance during the observation.

The original `tag-intersection` fixture tried to tag a marker at `4,64,2` with a
radius of 0.1 even though summon centered it at `4.5,64,2.5`. Its final predicate
could pass without an excluded fixture. The corrected case targets the actual
position and positively requires an excluded, unselected survivor. No negative
assertion was removed. Draft expansion box selectors also placed zero-size
markers on the lower box face; vanilla rejected those selections. The boxes now
enclose the markers. The original draft responses remain in
`artifacts/jaron-entities-vanilla-draft.json`.

## Current-source NBT list defect

Freshly fetched upstream master remains
`5b53f064af8708ba33fcaa533b81ca29a53a3310`. A bounded comparison uses the existing
immutable baseline binary and separate scratch-console servers because this
revision has no RCON. Every comparison holds the engine process lock; scratch
servers have memory/CPU limits and bind only to loopback.

On a marker with two tags, vanilla rejects `nbt={Tags:[]}` and a three-element
pattern containing repeated tags. Current upstream incorrectly accepts both.
Entity-existence and nonempty-subset positive controls pass on both targets;
the inverted empty-list predicate also differs. Each check is repeated twice.
The test uses entity conditions to write scoreboard sentinels and observes those
scores, since terminal `execute if entity` is unsupported in current upstream.

The fix adds the missing empty-list and list-size guards to the selector's NBT
matcher. It retains unordered subset matching, including reuse of a value when
the actual list is sufficiently long. The verified official server JAR was
decompiled locally with Vineflower 1.12.0: `NbtUtils.compareNbt` explicitly checks
both guards. Decompiled Java is private runtime material and is not published.
Two focused regression tests fail before the fix. Full validation and push
records are recorded in `artifacts/jaron-fork-status.json`.

The patched source commit is `31a781da7ec52a274bc8104a6875508f832e7055`.
All 435 `pumpkin-core` unit tests pass, as do workspace formatting,
core clippy with all targets/features, and the full binary build. The completed
three-target live comparison at
`artifacts/jaron-entity-console-20261015T214446.446756Z/report.json` passes all
eight controls twice on vanilla and patched code. Clean upstream fails the
empty-list, oversized-list and inverted-empty-list checks on both repetitions.
Controls also confirm empty actual lists and repeated subset values when length
permits. Both scratch servers stop cleanly without ERROR or panic log lines.
The original interrupted verification log is retained separately from the
successful detached build retry.

The open-upstream review found selector-permission PR #4069 and SNBT-depth PR
#4003, but no identical open NBT-list selector fix. Neither was integrated. Other
selector leads, including rotation-axis mapping and empty-tag handling, remain
outside this source patch.

## Reproduce and inspect evidence

```sh
python3 infra/author_scenarios.py
python3 -m unittest discover -s tests -p 'test_scenarios*.py' -v
python3 infra/validate_scenarios.py --target vanilla --repeat 2 \
  --id selector-nbt-empty-list --id selector-nbt-list-cardinality \
  --output artifacts/nbt-lists-vanilla.json
python3 -m lab run --targets runtime/targets.json --scenarios scenarios \
  --id selector-nbt-empty-list --id selector-rotation-axes \
  --id entity-effect-fields --id selector-distance-inclusive --repeat 2
```

`artifacts/jaron-entities-vanilla.json` snapshots the final definitions and raw
responses for all 48 vanilla expectation sets. The corresponding released
candidate evidence is `artifacts/jaron-entities-pumpkin.json`; candidate failures
are retained, not skipped or counted as distinct confirmed defects. Bounded
source reports are under `artifacts/jaron-entity-console-*/report.json`, with
complete scratch stdout retained at each report's `console_log` path. This is
not a full current-source catalog or RCON validation.
