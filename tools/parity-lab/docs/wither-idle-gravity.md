# Wither gravity after navigation stops

A Wither that has been flying can stop navigating after a visible target enters
its ranged attack radius. The campaign navigator clears its movement input but
leaves no-gravity enabled. The boss keeps floating instead of falling as on the
official server. This is distinct from waypoint selection and from the earlier
living-travel correction that makes active no-gravity effective.

Official Minecraft Java 26.3 installs `FlyingMoveControl(this, 10, false)` on a
Wither. During server AI, navigation supplies a wanted position; the controller
consumes that operation. On a later tick without a wanted position, the controller
restores gravity. NoAI skips that server AI work and retains the existing flag.
The Wither-specific vertical velocity damping still runs outside server AI.

Pumpkin's campaign navigator currently supplies flight input directly, while its
Wither retains the default movement controller. Installing an idle flying
controller alone would erase navigation input. Until the controller/navigation
integration is adopted, the Wither server AI hook mirrors the non-hovering
controller's gravity reset when navigation is done. The correction runs after
navigation and before living travel, skips NoAI, and leaves other flying species
and active routes alone. This patch does not change route selection or replace
the shared AI foundation.

The regression fixture `fixtures/wither-idle-gravity/cases.json` first lets a
powered Wither fly toward a lower stationary resistant villager for ten ticks.
For the ranged-stop case, it then places that target inside attack radius and
resets the boss position and velocity to compare the eight subsequent vertical
motion samples. The NoAI control disables AI after the same initial flight. The
continued-flight control runs another eight ticks without a command transition,
including its eventual navigation stop. Each case is repeated twice with a real
headless Java protocol-777 observer in a disposable arena. The checker compares
captured official positions and velocities within 1e-6 and checks actual gravity
metadata, health, phase, actor/client presence, controlled ticks and cleanup.
The fixture's commands are identical across server implementations.

Initial exploration reproduced zero vertical velocity on the campaign-88
baseline after the ranged stop, versus official -0.0784000015258789 on the first
idle tick. Official metadata changes from no-gravity true to false; the baseline
never clears it. That exploration also included an invulnerability interruption
whose route retention differs independently. Its failed evidence remains outside
the repository as a follow-up lead, and is not represented as passing coverage.

All 452 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock, one build
job and prescribed resource limits. The existing proc-macro-error2 future-
compatibility warning remains. The world/protocol fixture is the focused
regression coverage; it fails on the baseline, rather than asserting a copy of
the Rust condition in an isolated unit test.

Official and patched servers pass 371/371 checks; campaign-88 passes 349/371.
The 22 baseline failures are the ranged-stop gravity metadata and eight idle
vertical-motion samples per trial, plus gravity metadata and the final stopped
sample of the continued-flight control. Both trials agree. Final gameplay
commands, fixture and probe hashes match across targets. Each target advances
284 controlled ticks including cleanup. Source/binary, official-source,
client, oracle, checker, reports, logs and packet hashes are recorded in the
deployment artifacts. Cleanup, stopped processes, observer presence and clean
error-log checks pass.

Raw reports, client scripts, worlds, binaries and decompiled official source
remain outside the repository. Headless protocol/state evidence cannot prove client rendering,
Bedrock behavior, arbitrary routes, obstacle avoidance or a whole boss fight.
For a human check, observe a powered Wither pursue a lower target in an isolated
arena, move that target within attack radius, and confirm the boss resumes
falling; repeat with NoAI and continued pursuit.

The fork master was fetched and is already an ancestor of this campaign branch.
Current upstream still lacks Wither's flying-controller installation. Upstream
PR #4092's merged shared AI foundation and PR #4174's broader allay/navigation
work were reviewed for overlap; neither supplies this missing Wither-specific
idle reset. The separate initial construction bossbar-progress lead is already
fixed upstream and was not reimplemented. No upstream issue, PR or comment was
created. No separate upstream-master binary was built for this task.
