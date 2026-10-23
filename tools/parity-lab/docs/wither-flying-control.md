# Wither flight respects no-gravity

Withers following a target above or below them set their no-gravity flag, but
living travel still subtracted the gravity attribute. The boss therefore climbed
more slowly and descended faster than vanilla. Living travel now returns zero
effective gravity while the entity's no-gravity flag is set. Ordinary gravity
and slow-falling calculations remain in the existing path for other entities.

This is a narrow integration of behavior already proposed by MegalithOfficial in
[upstream PR #3657](https://github.com/Pumpkin-MC/Pumpkin/pull/3657), head
`64ea70727c635e912c6799e2aec6deee65da6dad`. Only the no-gravity guard in
`LivingEntity::get_effective_gravity` is adopted, in equivalent early-return form;
no gliding implementation is included. The deployment's `ops/FORK.md` permits
integrating existing fixes with attribution. This is not a novel upstream fix,
and no upstream PR, issue or comment was created.

Official Minecraft 26.3's final `Entity.getGravity` returns zero for `isNoGravity`
before `LivingEntity.getEffectiveGravity` applies slow falling. Air and fluid
travel call the latter. Pumpkin's flying navigator already sets flight input and
no-gravity, so the correction belongs in living travel. An initial attempt to
install a flying controller was rejected by actual runtime checks: the navigator
does not feed that controller, which remained idle and cleared movement input.
That source attempt and its binary are excluded; no controller change remains.

The focused fixture `fixtures/wither-flying-control/cases.json` uses a real
headless protocol-777 observer in isolated arenas. A Wither pursues a stationary,
resistant target above or below it; charging and NoAI controls run alongside,
each repeated twice. `vertical-motion.json` records official vertical positions
and velocities for the ten sampled ticks. The checker compares both trials to
those captured values with tolerance 1e-6, checks actual no-gravity metadata,
health, phase countdown, bounded finite movement, player/client presence,
Wither tracking, cleanup and controlled tick counts. Target health is queried;
its spawn packet is outside this observer's captured tracking audience.

The bounded climb and charging/NoAI regression passes 280/280 checks on official
and patched Pumpkin, versus 258/280 on the campaign-86 baseline. The full matrix
is deliberately retained: official 374/374, patched 350/374, baseline 328/374.
The patched server still fails 24 descending trajectory checks because the
navigator initially steers upward toward a waypoint when vanilla steers down.
These are failures, not parity passes. The gravity correction fixes climb
velocity; it does not establish descent parity. Both targets send the same
no-gravity metadata, distinguishing the flag from its physical effect.

All 450 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed with the shared Cargo lock, one build
job, disabled debug info/incremental and prescribed resource limits. The runtime
runs have identical probe/fixture/gameplay-command hashes, four cases twice and
306 controlled ticks per target. Source, binary, oracle, checker, official class,
client, packet, report and log hashes are recorded outside the repository. Clients
remain alive during observations; cleanup, process shutdown and error-log checks
pass. The existing proc-macro-error2 future-compatibility warning remains.

The final spawn is (5.5,90.5,15.5), with no command-created NoGravity on the
Wither. An earlier integer-coordinate matrix also exposed the descending
waypoint-input error and remains failed evidence. Centering did not resolve that
error. Both full reports are retained; only the climb/control subset is a passing
bounded regression. Navigation waypoint selection is the next gameplay lead.
No gravity changes are claimed for whole trajectories, arbitrary route choices,
obstacles, fluids, other entity types or boss fights. Pumpkin's missing NoGravity
NBT persistence is separate; actual metadata and physical motion establish the
flag's behavior here. This shared calculation affects other living callers, but
those paths have source/check validation only. No new implementation-mirroring
unit test was added; the focused world/protocol regression exercises the fix.
Headless evidence is not rendered-client proof.

For a human gameplay check, observe a Wither pursuing a stationary target above
or below it in a disposable arena, then repeat during charge and with NoAI.
Capture flight from a real client before any upstream submission. Probe scripts,
raw logs/packets/worlds, binaries and official source remain outside the repo in
the deployment workspace's assignment-87 artifacts.
