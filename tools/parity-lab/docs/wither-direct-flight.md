# Wither flying waypoint advancement

A powered Wither pursuing a stationary villager ten blocks below it reverses
horizontal steering on campaign 92. In the isolated Java 26.3 comparison, tick 7
reaches X=8.182137055126743 with yaw 270 on vanilla, but X=8.158137025227177
with yaw 90 on Pumpkin. The five-case level-flight fixture repeats level,
near-level, descending, spawn-charge and NoAI cases twice, sampling eight ticks.
Fresh vanilla passes 395/395 existing checks; the baseline passes 391/395.
Exactly four horizontal position/velocity checks fail: descending ticks 7–8
in each trial. Existing vertical, health/phase, gravity, observer, cleanup and
shutdown checks pass. Both runs use identical commands and fixture bytes.

Temporary baseline instrumentation confirms the missed waypoint: immediately
before tick 7, the Wither is at (7.692684128689536,100.36509317314851,15.5),
targeting node (7,99,15) with successor (8,98,15). Both the axis-arrival test
and geometric corner test reject advancement. The node remains behind the
Wither, so its horizontal input turns backward. The diagnostic binary reproduces
the same four failures; all diagnostic logging is removed from the patch.

Vanilla PathNavigation.shouldTargetNextNodeInDirection first requires a successor
and a current-node distance strictly below two blocks. It then calls the
navigation variant's canMoveDirectly before considering the directional fallback.
FlyingPathNavigation implements this with a collider ray, including all fluids,
from the mob position to the current path node's entity destination plus half
the mob height. Pumpkin omitted that branch and used only the geometry test.

The Rust correction supplies the flying direct-movement check at this decision
point, retaining the existing danger-node exclusions, successor requirement and
geometric fallback. Ground navigation still supplies false, as vanilla's base
canMoveDirectly does. The shared distance guard now also excludes exactly two
blocks. Other flying-navigation users receive this same correction; their full
gameplay behavior is outside the bounded Wither check.

The focused Rust regression fails on the original source with index 0 instead
of 1 for the captured position and path nodes. Final coverage distinguishes
clear and blocked movement, verifies the queried destination is the current
entity waypoint, and preserves terminal, dangerous-node and radius guards.
Existing arrival-boundary and route-retention tests remain in place. The
runtime fixture exercises the actual sensing/goals/navigation/travel chain.

Fetched fork master is already an ancestor. Current upstream master retains the
missing direct-movement shortcut. The initial overlap check found no equivalent
change in open PRs #3955 and #4174. The final refresh found a new concurrent
[PR #4183 by AdmerPRO](https://github.com/Pumpkin-MC/Pumpkin/pull/4183), opened
at 14:26:29 UTC with head 6918ef255b2fea40c03989f3cb693a6d6f7918f6. It includes
an equivalent direct-clear shortcut and collider/fluid check, alongside broader
arrival, passenger and stuck-detection corrections. This campaign patch was
prepared independently before that PR appeared; no code was copied. It adapts
the missing behavior to the retained campaign navigation architecture and does
not claim an uncovered upstream defect. The broader PR is not integrated here.
The spawn-invulnerability goal is already fixed by earlier campaign work and
was not selected again. Provider-rejected work remains excluded.

Workspace formatting, all 456 core Rust library tests, core all-target/all-feature
Clippy and the debug server build pass under the shared Cargo lock, one build
job and the prescribed resource caps. The existing proc-macro-error2
future-compatibility notice remains.

Fresh vanilla and patched Pumpkin pass 395/395 arena checks; baseline passes
391/395 with exactly the four descending horizontal failures. Across all 80
sampled yaw comparisons, vanilla and patched pass 80/80; baseline passes 76/80
with the same four descending failures. Yaw is compared modulo 360 within
0.001 degree; position/velocity within 1e-6. Each target advances 356 controlled
ticks. The patched tick 7 reaches X=8.18213702618085 with yaw equivalent to 270,
matching vanilla within tolerance instead of turning backward.

The existing fixture and checker are unchanged. Identical probe, fixture and
gameplay commands, source/binary/official-source/report/packet/log hashes,
health/phase, gravity, live observer/player, cleanup and stopped-process checks
are verified. Successful server logs contain no errors or panics. Deployment
evidence stays outside the repository, including the temporary waypoint trace;
decompiled Java, binaries, worlds and scratch observers are not published.

This is headless Java protocol/server-state evidence. It does not prove rendered
client behavior, Bedrock, pitch/body/head rotation, arbitrary paths, obstacles,
fluid avoidance or a whole boss fight. A human check should compare an isolated
powered Wither pursuing a resistant villager below it on vanilla and Pumpkin;
record the early approach and confirm that the boss keeps steering toward the
villager instead of briefly turning back.
