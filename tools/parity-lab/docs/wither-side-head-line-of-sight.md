# Wither side-head line of sight

Pumpkin's side heads acquire targets through opaque blocks and fire without rechecking visibility. Require an eye-to-eye block raycast both when selecting a side-head target and before firing at the current target. A hidden current target is cleared through the existing invalid-target branch.

Baseline: campaign commit `0060dc6e436fe5c347c467b1f1eb702f53c397ff`, containing fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844`. Its Wither source is unchanged from upstream master `5b53f064af8708ba33fcaa533b81ca29a53a3310`.

## Vanilla comparison and upstream overlap

Compared the official Minecraft 26.3 `WitherBoss.customServerAiStep`, `TARGETING_CONDITIONS`, `TargetingConditions.test`, sensing and `LivingEntity.hasLineOfSight`. Vanilla filters acquisition using combat targeting conditions with sight enabled, then checks sight before each targeted side-head shot. The official jar was inspected privately with Vineflower 1.12.0 and javap; no game source or binaries are committed.

Use the entity raycast directly: Wither currently runs its custom tick before generic mob sensing is reset, so the sensing cache could retain the previous tick's visibility after a wall appears. Vanilla uses `COLLIDER` and ignores fluids. Pumpkin's entity helper names its mode `Visual`, but the current clip implementation maps both `Visual` and `Collider` to the same collision shapes. Revisit that alias if shared visual occlusion shapes are implemented separately; no shared entity/world file is changed here.

The [tracker](https://pumpkinmc.org/tracker/) and [mob AI issue #3468](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) provided leads. The issue's description of missing Wither attacks is stale for this source. The missing spawn-window goal remains separate. Open upstream PR #3865 covers Nether Star drops and #4038 covers Wither Skeletons; neither implements this visibility correction. Final read-only overlap search found no identical open fix. No upstream issue, PR or comment was created.

## Regression coverage and results

The focused fixtures are `tools/parity-lab/lab/examples/wither-side-head-blocked.json` and `wither-side-head-visible.json`. An ordinary stationary iron golem stands outside a bedrock cage containing the Wither. Each case verifies one entity-registration tick, then samples skull presence for 40 ticks. Expect zero samples with a closed cage and at least one with an open east wall. Easy difficulty disables idle dangerous skulls. Initial/final wall checks and target-presence checks guard the arena conditions.

Use fresh isolated worlds per case and repetition. A headless offline protocol-777 client holds Pumpkin's chunk loaded while observations use scratch console commands; vanilla uses RCON and its working force-load mechanism. This client does not render or provide visual proof. Earlier chunk-unload/loader attempts are retained privately and excluded from validation; disappearing blocks there do not establish a separate gameplay bug.

Final comparison: `artifacts/jaron-wither-live-20261016T075431.497543Z/report.json`, with completion assertions in `artifacts/jaron-wither-completion.json`. Twelve fresh-world cases completed (three binaries, two cases, two repetitions), each verifying 41 ticks. The baseline closed-cage trials produced 6 and 7 skull-present samples while initial and final bedrock checks passed; its open-wall controls produced 11 and 11. Vanilla and patched Pumpkin each produced zero closed-cage samples in both repetitions, while all open-wall controls fired (vanilla 12/12 samples; patched 10/14). Each passed all 20 explicit fixture assertions plus four environment guards. Every scratch server stopped. Skull counts are presence samples, not a comparison of attack rate, trajectory or damage.

The fixture notes were clarified after the run to require the actual working protocol-client loading method; setup, steps and cleanup are unchanged.

Workspace formatting, all 443 core unit tests, core all-targets/all-features clippy and the full binary build passed under the shared Cargo lock, one job, disabled debug info/incremental compilation, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. The existing `proc-macro-error2` future-incompatibility warning remains. Results: `artifacts/jaron-wither-verify.json` and `artifacts/jaron-wither-build.log`. Patched binary SHA-256: `5e5aa8e0d39d2cc3a8e4fdcb004ff67369ab741c0d9d140fa4558b15a05d3579`.

## Limits and next Wither leads

This bounded comparison covers initial target acquisition and visible firing. Losing sight of an already acquired target is corrected in the firing branch but needs a separate live transition check. No human client capture or whole-fight parity is claimed. Side-head targeting range, combat eligibility, projectile flight/damage, other boss phases and drops are outside this patch.

* Missing priority-zero `WitherDoNothingGoal` while `Invul > 0`: reproduce visible head behavior before patching.
* NoAI still advances custom Wither AI countdown, healing and skull work: reproduce separately.
* Side-head acquisition lacks vanilla's spherical combat range and full `canAttack` eligibility; treat each as a separate reproduction.
* Nether Star death/drop behavior overlaps upstream PR #3865; inspect it rather than duplicating it.

## Human play test

Join vanilla and patched servers with a real client. Put a stationary iron golem behind a solid bedrock wall: side heads should not fire at it. Open the wall and expect attacks; close it again and expect targeted fire to stop. Record the boss, target and opening/closing transitions. Before any human upstream submission, play-test and attach that recording; console observations and the headless client do not replace it.

Capture: <attach screenshot or recording here>
