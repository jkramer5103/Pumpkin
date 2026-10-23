# Fight-created dragon spawn transform

The dragon fight manager created dragons at `(originX + 0.5, originY + 128,
originZ + 0.5)` and left their yaw at zero. Vanilla 26.3
`EnderDragonFight.createNewDragon` calls `snapTo` with integer origin X/Z,
128 above the origin, zero pitch and `nextFloat() * 360` yaw. This affects both
the first dragon and a dragon created at the end of a crystal respawn ritual.

The Rust creation path now uses those integer coordinates and samples its yaw
before `spawn_entity_non_save` registers the tracker. Only boss fight creation
changes; command summons use their existing path. Position construction still
initializes the bounding box normally. Yaw is stored directly because vanilla
`Entity.snapTo` sets body orientation without overwriting the living constructor's
separate head yaw. Pumpkin's shared living constructor remains outside this fix.

A fresh isolated official 26.3 arena sends a dragon spawn packet at `(0,128,0)`
with yaw 317.8125 degrees (decoded signed byte: -42.1875). The same focused
setup using the immutable campaign86 binary sends `(0.5,128,0.5)` and yaw zero.
Both servers boot, reach the fight with a connected creative headless player,
report phase 0 and 200 health, and clean up and stop normally. The committed
`fixtures/dragon-fight-spawn/cases.json` and
`tests/check_dragon_fight_spawn.py` check the actual spawn packet rather than
position queried after flight has begun. The checker passes vanilla and rejects
the old binary's half-block offset. Packet yaw is normalized modulo 360; random
zero is legal, so a single nonzero sample is not used as a statistical test.

All 495 core Rust library tests, workspace formatting, core Clippy with all
features/targets and the debug server build pass under the shared Cargo lock
and resource limits. The existing `proc-macro-error2` future-compatibility
warning remains. The patched binary passes the focused checker, sending
`(0,128,0)` with yaw 59.0625 degrees, zero pitch and zero initial velocity.
Phase, health, live player/client, cleanup and shutdown checks pass for all
three targets; successful server/client logs contain no error or panic lines.
Source, immutable binary, official jar, probe, clients, fixture, checker and
report/packet/log hashes are recorded in the task's runtime artifacts.
The headless clients are terminated after observation and do not emit their
final client JSON; live connection, player presence and received packets are
retained. No new Rust unit test duplicates world construction; the focused
packet regression exercises the real creation path and fails on the baseline.

Current fork master is already an ancestor of this branch. Read-only upstream
master retains the same offset and absent yaw initialization. Open dragon PRs
3661 and 3407 cover multipart hitboxes and related tracking/combat changes;
neither changes this spawn transform. The other lane's shared living/mob files are not
touched. No standalone upstream-master binary was built.

One fresh run per target provides bounded protocol/server-state evidence.
Vanilla uses the existing original client72; Pumpkin uses existing client86
with its stationary position update required for chunk streaming. Both use the
same probe logic and explicit central chunk readiness gate. There is no real
rendered-client, full fight, random distribution, nonzero fight-origin,
respawn-ritual-after-this-patch, save/reload, plugin or Bedrock proof. The prior
assignment86 ritual packets independently exhibit this same defect, but that
ritual is not rerun as part of this initial-spawn task.

For a human visual check, enter an isolated fresh End and record the first
dragon appearing centered on integer `(0,128,0)` with a varying flight heading.
No real-client recording has been produced by this task.
