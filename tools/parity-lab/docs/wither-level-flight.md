# Wither flight near level waypoints

A Wither flying toward a target at its own height initially hovered in the
campaign branch instead of descending. Official Minecraft Java 26.3 produced
vertical velocity `-0.01176000043332576` on the first tick; campaign 89 produced
zero. The same difference occurs when the boss starts 0.05 blocks above the
waypoint. Both cases reproduced twice in a disposable arena.

Vanilla `FlyingMoveControl.tick` sets signed vertical input whenever either the
vertical offset or horizontal distance exceeds its small direction epsilon.
When the waypoint is at the same height but ahead, the non-positive vertical
offset selects downward input. The retained campaign flying navigator instead
required a vertical offset greater than 0.1 and otherwise wrote zero. Its extra
dead zone also suppressed input when approaching from slightly above or below.

The correction applies the existing controller's condition and preserves the
previous vertical input when neither direction component exceeds the epsilon.
This is a narrow adaptation of the signed-input behavior already present in
the flying controller and the merged
[AI foundation change #4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092),
commit `a1867b33ca90b483334ab2e54bb2e9113b7da94e`.
The campaign still supplies flight input through navigation; this does not
merge the shared AI rewrite. Wither is the only mob that instantiates a flying
navigator in this checkout. PR #4174 changes waypoint following for allays on
the newer controller architecture; #3955 changes search budgeting and caching.
Neither patches this retained input calculation. Fork master was fetched and is
already an ancestor. No upstream publication was made.

The regression fixture `fixtures/wither-level-flight/cases.json` covers level
and near-level pursuit plus descending, charging and NoAI controls. Each case
runs twice for eight sampled ticks with an actual headless protocol-777 observer.
The checker compares vertical position and velocity with captured official
output within 1e-6, effective no-gravity metadata, phase and health, actor/client
presence, controlled ticks, arena bounds and cleanup. Redundant metadata writes
of the default false value are normalized; packet count parity is not claimed.
Commands and fixture are identical on all three targets. The full eight-tick
matrix reports official 315/315, baseline 283/315, and patched 303/315. Twelve
later vertical trajectory failures remain on the patch: level ticks 5–8 and
near-level ticks 7–8, in both trials. They remain failures in the checker and
recorded evidence. Descending, charging and NoAI controls pass throughout.

The verified correction is initial vertical input. The separately reported
`initial_input_and_controls` result compares the first three pursuit ticks and
all controls: official and patched 295/295, baseline 283/295. The first three
ticks cover input and acceleration before subsequent waypoint selection
separates. This scope was narrowed after the longer trace exposed the remaining
route defect; it is not an eight-tick trajectory pass. The retained full trace
prevents that distinction from being hidden. No additional Rust unit test copies
the input expression; the real world/protocol regression detects the old input
error.

Workspace formatting, all 452 core library tests, core all-target/all-feature
Clippy and the debug server build pass under the shared Cargo lock, one job and
prescribed resource caps. The existing proc-macro-error2 future-compatibility
warning remains. Each runtime target advances 356 controlled ticks. Identical
probe/fixture/gameplay commands, actual client and actor presence, cleanup,
shutdown, clean error logs and source/binary/oracle/checker/packet/log hashes are
verified in the deployment manifests.
Raw reports, binaries, worlds, observer scripts and decompiled Java remain in
the deployment artifacts outside the repository.

This is bounded headless state/protocol evidence, with no rendered-client,
Bedrock or whole-fight proof. Horizontal speed, pitch turning, obstacles, fluids,
arbitrary routes and long-term AI timing are outside this correction.
`PathNavigation.set_progress` still clears the path on every ranged-goal update;
this overlaps upstream PR #3955 and can change the rounded start height as the
boss crosses a half-block. The later divergence needs separate root-cause
isolation and overlap review before another source correction. For a
human check, observe a powered Wither pursue a resistant target at the same
height in an isolated arena and compare the initial descent with vanilla.

The previous charging-interruption lead is excluded: its setup teleported the
boss, which calls vanilla `Mob.stopInPlace`. Vanilla's invulnerability goal has
no navigation-stopping override. That probe does not establish a spawn-goal bug.
