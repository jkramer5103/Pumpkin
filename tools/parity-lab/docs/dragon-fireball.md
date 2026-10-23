# Traveling dragon fireballs

Strafing previously created a breath cloud directly at the target player. It now
launches a `dragon_fireball` from behind the head toward the player's midpoint.
The projectile accelerates before sweeping blocks and entities, and creates a
breath cloud only on impact. Impact breath starts at radius 3 and grows toward 7
over 600 active ticks, with the usual 20 tick wait. Shot and splash world events
respect the dragon/projectile silent flags. No shared fireball physics is changed.

Before evidence: official 26.3 launches one fireball and no cloud at each of two
natural strafe shots. Campaign81 produces one immediate cloud and no projectile
in both samples. Acquisition, five tick charge, survival target, line of sight,
player presence and cleanup controls pass. The isolated probe preserves the
actual naturally acquired strafe target; it does not assign a target through NBT.

The regression fixture covers two natural shots and 14 controlled projectile
cases: air, diagonal, stationary, acceleration disabled, wall, sheep and player
collisions, each repeated twice. Controlled projectile coordinates are centered
by the command parser (for example `summon ... 8 120 8` starts at 8.5/120/8.5).
The checker compares ten per-tick positions, velocities, projectile/cloud presence
and impact cloud positions against the official server.

494 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build pass under the shared Cargo lock, one build
job, disabled debug/incremental output and the required memory/CPU limits.
Final-source Pumpkin passes all 700 per-tick projectile comparisons; campaign81
passes 352/700 and differs on 348 flight/impact observations. The two natural
strafe shots pass all 14 launch/travel checks on official and final-source
Pumpkin; campaign81 fails all 14. All 216 positive radius metadata samples and
six silent splash packets agree. Per-case stimulus commands, controlled tick
progression, player presence, cleanup and stopped-process controls pass. The
successful server logs contain no errors or panics. Source, binary, fixture,
probe, official-source, packet, report and log hashes are recorded in the local
`artifacts/christine-dragon82-live-validation.json` evidence file.

The final binary SHA-256 is `9efff3fe09bfc5aec1ad03719962d12fdc776be75666327e7f8338371a2c5930`.
The build manifest records the parent commit and modified Rust file hashes;
committed-source provenance is recorded separately after the patch commit.

Coverage is headless protocol/server-state evidence. No rendered-client,
Bedrock, whole-fight, reload or full 620 tick cloud lifecycle proof is claimed.
Water, world borders, deflection, root vehicles and shared cloud owner/damage
attribution remain unasserted. Natural shots use a naturally acquired target,
then controlled teleports; exact randomized head/path trajectories are not
compared. Later auxiliary sheep observations reveal a separate shared corpse
removal difference: official removes the dead sheep, while Pumpkin retains its
health-zero corpse at the last observation. That is excluded from parity passes.
Earlier floating-kick, setup/readiness, generated-script, compile/const-lint and
below-6-GiB build attempts are excluded. Only older Christine binaries 77-80 were
losslessly compressed, with original/decompressed hashes checked; the archive
record remains local. Existing `proc-macro-error2` future-compatibility and normal
offline/debug/Java startup notices remain.

Upstream overlap: master 9c04f714b still creates the immediate strafe cloud and
has no dragon-fireball type dispatch. Open PR3835 changes shared fireball and
thrown-item physics, but implements no dragon-fireball entity or strafe launch.
The new entity has its own movement/collision lifecycle. PR3407/3661 multipart
work and PR3694 crystal combat work remain deferred. No upstream messages or
pull requests were sent. Fork master 65bca3f7f is already an ancestor of this lane.

## Dеscription ·

> This description was drafted by an AI agent (Codex, gpt-6.1-sol).

Strafing dragons now shoot a traveling fireball instead of placing breath at the
player immediately. Impact creates the expanding dragon-breath cloud.

## Tеsting ·

494 Rust tests, formatting, Clippy and build pass. The bounded headless
comparison passes 700 projectile and 14 natural-shot checks against official
26.3, plus 216 growth samples and six splash packets. With a real client, bait a flying dragon into strafing and
move sideways after its shot: expect the visible projectile to travel from its
head, with breath appearing at impact. Repeat behind a wall and observe impact
at the wall. Capture the launch, flight and cloud appearance in one recording.

Capture: <attach screenshot or recording here>
