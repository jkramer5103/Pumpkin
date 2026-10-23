# Wither horizontal movement input ordering

A powered Wither pursuing a stationary target accelerates slightly too slowly
on campaign 91. In a fresh isolated Java 26.3 arena, the first level-pursuit
step reaches X=5.512000000208616 on the official server and X=5.511760000467301
on Pumpkin. At tick 8 the positions are X=8.672297917871802 and
X=8.669494919218652. The existing level-flight fixture runs level, near-level,
descending, spawn-charge and NoAI cases twice for eight sampled ticks each.
Official passes 395/395 checks; the baseline passes 347/395. All 48 failures
are horizontal position/velocity comparisons in the three active-pursuit cases.
The existing vertical, phase, health, actor/client, gravity, cleanup and shutdown
checks pass on both targets. The commands, fixture and observer are identical.

Vanilla LivingEntity.aiStep calls applyInput before serverAiStep. Input damping
therefore prepares the previous inputs; navigation and controllers can replace
them with fresh input before travel. The campaign branch instead runs AI in
Mob.tick, then damps the newly produced horizontal input in living movement.
The correction moves the existing server_ai_step call to the living movement
boundary immediately after damping and before jumping/travel, retaining its
NoAI gate and avoiding a second AI call.

This is a narrow adaptation of the execution ordering already merged through
[MegalithOfficial's AI foundation PR #4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092),
merge commit a1867b33ca90b483334ab2e54bb2e9113b7da94e. Current upstream already
contains that ordering. It is a correction to the retained campaign architecture,
not a new upstream defect claim. The rest of the navigation/controller rewrite
is excluded. Fetched fork master is already an ancestor; no history is rewritten.
The invulnerability-window goal from tracking issue #3468 is already implemented
and was not selected again. Provider-rejected work remains excluded.

The moved call serves all Mob implementations, including ground, swimming and
flying mobs. Their sensing, goals, navigation and custom AI now run after the
base entity tick, zero-velocity preparation and previous-input damping, and
before jump/travel physics. Player movement still uses its existing client
movement path. Non-mob living entities keep their existing input damping.
Species mob_tick and post_tick hooks remain in place. NoAI continues to skip
server_ai_step and travel. This focused Wither arena does not establish gameplay
parity for every shared caller, death scheduling, fluids or changing targets.

Focused regression coverage adds captured official horizontal position and
velocity to the existing level-flight fixture and checker, with a 1e-6 absolute
tolerance. Both official trials agree within that tolerance. It exercises the
real AI/navigation/travel chain; no Rust unit test duplicates the damping
expression. Deployment-only reports hash the official jar, reference source,
baseline binary, observer, fixture, oracle and checker. Raw logs, worlds,
binaries, observer tools and decompiled Java stay outside the repository.

Workspace formatting, all 454 core Rust library tests, core all-target/all-feature
Clippy and the debug server build pass under the shared Cargo lock, one build
job and the prescribed resource caps. The existing proc-macro-error2
future-compatibility notice remains. Runtime regression supplies the focused
red/green coverage for the real movement chain rather than a new unit test.

The full matrix reports official 395/395, baseline 347/395 and patched 391/395.
Forty-four previously failing horizontal comparisons now pass. Four later
horizontal comparisons remain failed: descending ticks 7–8 in both trials.
At tick 7, baseline and patched Pumpkin both reverse yaw to 90 degrees while
official remains at 270 degrees. The navigation/controller cause of that later
reversal needs separate isolation; the initial input fix does not correct it.
Those failures are retained in the checker and manifests; full eight-tick horizontal parity is not claimed.

The separate input_order_and_controls result covers the six earlier descending
ticks, all eight level and near-level ticks, all vertical comparisons and the
charging/NoAI/environment controls. It excludes only the four named later
horizontal comparisons. Official and patched pass 391/391; baseline passes
347/391. This bounded result demonstrates the input-order correction; the full
395-check result above shows its practical limit. Each target advances 356
controlled ticks. Identical probe, fixture and gameplay commands, clean successful
logs, cleanup/shutdown and source/binary/official/oracle/client/report/packet/log
hashes are verified in deployment manifests.

Headless protocol/server-state evidence cannot establish rendering, Bedrock,
arbitrary paths or a whole boss fight. A human check should compare an isolated
powered Wither pursuing a resistant level target on vanilla and Pumpkin, including
both horizontal acceleration and the previously corrected vertical settling.
