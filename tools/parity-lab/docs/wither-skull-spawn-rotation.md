# Wither skull initial rotation

Wither skulls used their launch vector to initialize yaw and pitch. Vanilla's
living-shooter `AbstractHurtingProjectile` constructor assigns directional
movement, then copies the shooter's yaw and pitch. Nonliving skulls report zero
head yaw through `Entity.getYHeadRot`. A shot along positive X could therefore
spawn facing the opposite direction in Pumpkin, with an incorrect pitch and
head yaw in the spawn packet.

The skull constructor now inherits shooter yaw and pitch without assigning a
separate head yaw. Movement and the existing launch-speed correction remain
independent of orientation. The only gameplay caller is
`WitherEntity::perform_ranged_attack`; all three heads use this constructor.
Ownerless/summoned skull construction is unchanged.

Official 26.3 source reviewed locally: `WitherBoss.performRangedAttack`,
`WitherSkull` constructor, `AbstractHurtingProjectile` constructors, and
`Entity.setRot`/`getYHeadRot`. Current upstream retains the faulty constructor.
Open PR 3835 covers shared projectile flight, collisions and hit effects but
does not modify initial skull rotation. PR 4092 has merged upstream and does
not fix this constructor. Fork master is already an ancestor of this branch,
with no additional campaign changes to integrate.

Regression coverage uses two trials of four shot directions plus a coincident
zero-vector control. Before each frozen tick the boss is reset to yaw 37,
pitch -17, zero velocity and the same position. Horizontal target offsets stay
within three blocks, avoiding flight yaw changes. The newly fired main-head
skull is read at its exact launch origin before any projectile flight tick.
NBT rotation must be `[37.0f,-17.0f]`; the headless protocol observer must receive
yaw 36.5625, pitch -18.28125 and head yaw zero after byte-angle packing. The
checker also verifies velocity, origin, target/boss health, controlled ticks,
observer survival, command errors, cleanup and stopped processes.

Vanilla passes 110/110 focused checks; campaign 76 baseline passes 90/110,
failing exactly the 20 initial NBT/spawn-packet rotation checks. Each target
advances 686 verified ticks using identical commands apart from game-time
polling. Both scratch servers stop cleanly and cleanup passes.

Patched Pumpkin passes the same 110/110 checks. Workspace formatting, all 450
`pumpkin-core` library tests, core all-target/all-feature Clippy and the debug
server build pass under the shared Cargo lock with one build job, debug info
and incremental compilation disabled, and the required 5 GiB/200% CPU scope.
Source and copied-binary hashes match the live run; fixture, checker, probe,
command and server/client log hashes are recorded locally. Logs contain no
errors or panics; known startup warnings and the existing `proc-macro-error2`
future-compatibility notice remain. These focused checks validate initial
rotation only.

Limits: server NBT and real headless protocol packets only. No rendered-client,
Bedrock, later-flight, collision, damage attribution or whole-fight proof.
Side heads share the corrected constructor but are not the measured main-head
cases. Shared projectile flight remains separate work overlapping PR 3835.

Manual visual check: in an isolated arena, let a Wither fire while turning;
record the skull's initial facing before its first movement update and compare
with vanilla. Capture: a real-client recording is still required for visual
proof. No upstream PR or issue was opened.
