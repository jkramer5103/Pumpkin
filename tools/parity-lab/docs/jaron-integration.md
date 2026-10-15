# Jaron integration notes

The current upstream baseline built successfully in 9m39s from
`5b53f064af8708ba33fcaa533b81ca29a53a3310`, under the shared cargo lock and
required resource limits. It booted as the candidate, but this upstream revision
has no RCON implementation or configuration (no references in pumpkin,
pumpkin-core or pumpkin-config). Port 25586 never opened. After the interrupted
readiness attempt, the original released binary/configuration was restored
under the engine lock and RCON/gamerules were verified again. Source-baseline
command parity is **untested**, not 0/50. Attempt provenance is recorded in
`runtime/manifest.json.source_baseline_attempts` and
`artifacts/jaron-upstream-deployment.json`; the incomplete comparison artifact
has zero completed results. See `artifacts/jaron-fork-status.json` for patch status.

The catalog now contains 50 behaviors. All 50 met positive expectations twice
on live vanilla (`artifacts/jaron-catalog50-vanilla.json`). The released candidate
met none (`artifacts/jaron-release-catalog50.json`). Its unloaded chunks and
unsupported terminal execute predicates prevent interpreting this as 50
independent gameplay defects.

Files owned by the engine lane were read but not edited. The attempted bounded
engine run is retained at
`artifacts/runs/20261015T210048.698585Z-0275a6be`; it exited 2 after the first
scenario, with candidate environment errors. The CLI accepts a single `--id`;
repeated flags select only the final value, so this invocation did not execute
all four requested IDs. Use a scenario directory subset or individual invocations.

Current upstream block command findings for integration:

- `BlockArgumentType` parses only a material name. Placement states/NBT and clone
  state filters are separate capability gaps. Changes to execute predicates
  belong to the engine lane; no execute code is changed by Jaron.
- `BlockPredicate::test` currently compares only the material/tag membership;
  fill supplies the material without its actual state. This is the focused
  source-fix investigation in the Jaron lane. NBT matching is a separate gap.
- `forceload add` updates the forced/active set but does not fetch chunks in this
  headless setup. A successful command is insufficient readiness evidence.

Vanilla implementation was inspected locally using Vineflower 1.12.0 on classes
from the verified official 26.3 server JAR. Decompiled files stay under runtime
and are never committed. `BlockPredicateArgument.BlockPredicate.test` compares
specified state properties; `TagPredicate.test` rejects missing/invalid shared
properties. Unknown placement/state/NBT support must remain visible in reports.

Open-upstream overlap review found existing issue [#2592](https://github.com/Pumpkin-MC/Pumpkin/issues/2592) documenting forceload/state-parser/execute gaps. [PR #3827](https://github.com/Pumpkin-MC/Pumpkin/pull/3827) covers setblock state parsing; [PR #3964](https://github.com/Pumpkin-MC/Pumpkin/pull/3964) covers fill callbacks. Neither is claimed as new work here, and neither was cherry-picked.

The engine treats intentional failing mutations as command problems even when the final state expectation passes (occupied keep, rejected overlap and nonmatching fills). This remains visible. Supporting an explicit expected-failure schema belongs to the engine lane; Jaron does not hide or weaken these cases to obtain engine passes.

Fill-filter regression reproduced on current source: the focused test failed with original matching (`minecraft:oak_log[axis=x]` incorrectly returned true for a default y-axis log). The source patch adds state-aware matching and changes fill to pass each cell's actual state ID. Named and tag constraints check only supplied properties using generated metadata. Full command-crate tests are running; source-binary validation is still pending. Block-entity NBT filtering remains outside this patch.
