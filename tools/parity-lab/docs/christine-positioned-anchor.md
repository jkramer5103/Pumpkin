# Execute positioned anchor reset

Upstream master `5b53f064af8708ba33fcaa533b81ca29a53a3310` retains an eye anchor after explicit `execute positioned` coordinates. Vanilla Java 26.3 resets it to feet. Later local coordinates therefore start above the intended position in Pumpkin. The fix resolves coordinates first, then resets the copied source anchor. The positioned-as modifier is unchanged, matching vanilla.

The regression uses the actual dispatcher parser and positioned modifier with absolute and relative coordinates. It checks the resulting position and feet anchor, and that the original source remains eyes. It failed against unchanged upstream with Eyes != Feet. After the fix, all four execute tests passed with Cargo exit 0. The changed Rust file passes rustfmt --check and git diff --check.

Commands actually run:

- Before the fix: `cargo test --locked -p pumpkin-core positioned_coordinates_reset_the_entity_anchor --lib`.
- After the fix: `cargo test --locked -p pumpkin-core command::commands::execute::tests --lib`.
- Patched binary: `cargo build --locked -p pumpkin` (exit 0).

All Cargo operations held the shared build lock, used one job, disabled debug info and incremental compilation, and ran in scopes capped at 5 GiB memory, no swap and 200% CPU. The built source commit was `f123eb8383eda4f6edbdcd71d840086901a4b339`; its binary SHA-256 was `024e318a82ed3b50ca4ae687dbf272a2d60d5fa952d9bb5266bc2b3c927b5fe9`. The subsequent documentation commit does not change that binary's source.

## Bounded live validation

A two-repeat probe compared vanilla 26.3 over RCON, unmodified current-upstream Pumpkin through its console, and the patched binary through its console. Scratch servers bound only to loopback on ephemeral ports, used independent worlds, ran under memory/CPU caps, and stopped cleanly. The entire comparison held the engine's shared file lock.

The probe summoned an armor stand at 2.5 64.25 2.5, ran `anchored eyes positioned ~ ~ ~`, then summoned a marker using local coordinates. In both repeats:

| Target | Source exists | Marker exists | Marker position | Marker at feet |
| --- | --- | --- | --- | --- |
| Vanilla 26.3 | yes | yes | [2.5d, 64.25d, 2.5d] | yes |
| Upstream 5b53f064 | yes | yes | [2.5d, 66.0275000333786d, 2.5d] | no |
| Patched f123eb8 | yes | yes | [2.5d, 64.25d, 2.5d] | yes |

Entity-condition outcomes were explicitly recorded into scoreboard values and checked with terminal score predicates. Current upstream rejects terminal execute-if-entity assertions; the initial unsupported probe remains in evidence. No response normalization hides that gap. The current-upstream source has no RCON implementation/configuration, so this console probe validates the targeted state change rather than the full RCON catalog. The live released candidate was not replaced by this patch.

Original vanilla 26.3 ExecuteCommand was checked using a local targeted decompilation of the verified official server JAR; no decompiled code is committed. Open upstream positioned/entity-anchor searches were checked before implementation and rechecked before handover; no matching fix was found. No upstream PR or issue was opened.

Live-lab evidence: `artifacts/christine-upstream-anchor-test-before.log`, `christine-upstream-anchor-test-verify.{log,json}`, `christine-source-binary-build.{log,json}`, `christine-built-binary.json`, and `christine-console-20261015T212013Z/report.json` with original per-server logs. The full 50-scenario released-candidate catalog was also run twice: all vanilla positive assertions met; all 50 candidates were infrastructure errors with unsupported/failed assertion evidence retained, zero flakes and zero confirmed mismatches. That catalog does not validate current-source behavior.

Clippy, the full Rust workspace suite, player gameplay and client rendering were not tested. This is command-observable state validation.
