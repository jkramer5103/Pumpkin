# Dragon breath contact volume

Pumpkin tested cloud victims inside a sphere with the cloud radius. Vanilla
26.3 `AreaEffectCloud.tick` first selects living hitboxes intersecting the
cloud's box (extending one radius horizontally, 0.5 blocks high), then checks only the
victim position's horizontal distance. Pumpkin therefore damaged sheep above
and below a flame and missed a sheep near the outer edge whose body overlapped
the flame but whose feet were one block below it.

`AreaEffectCloudEntity` now builds candidate bounds using the generated cloud
height and checks squared horizontal distance. Existing waiting, expiry,
reapplication, radius-on-use and duration-on-use handling stays in place. The
existing duration-effect distance scale now uses horizontal distance; uniform
instant potency is already handled by the potion application source. Timed
potion duration scaling remains a separate parity lead.

This shared path also serves lingering potions, the existing strafing cloud,
and generic clouds. They use the same thin contact volume in vanilla. Their
spawn paths and plugin events are unchanged. No living/combat APIs change.

## Focused evidence

`dragon-breath-contact-volume.json` emits a real sitting-dragon flame twice in
an isolated seeded overworld chunk. After emission it pauses and moves the
dragon away, clears terrain below the cloud, and spawns stationary sheep at
the actual cloud position and relative offsets. It checks health and exact
positions after twenty ticks: center and vertically overlapping sheep lose
three health, while sheep wholly above/below and beyond the horizontal radius
stay healthy. A connected headless protocol client keeps the arena active.

Reference: vanilla passed 41/41 checks. Baseline Pumpkin at d62351a passed
33/41, failing precisely four health checks per trial: two above-cloud victims,
one below-cloud victim, and one vertically overlapping victim near radius 5.
Patched Pumpkin also passed 41/41. All position and tick-delta controls passed
on all targets (60 controlled ticks each). All three scratch processes stopped;
both Pumpkin saves completed. Logs contain no errors or panics. Vanilla final
save completion was not confirmed within the harness shutdown grace period.

The first scratch fixture retained a floor intersecting the below-cloud sheep
and also expected integer teleport coordinates without Minecraft's horizontal
centering. That run is retained locally, but does not count as passing evidence.
The final fixture clears the floor after emission, records actual cloud
positions, and verifies every victim position.

The Rust regression exercises vertical overlap and exact top/bottom contact
boundaries. The build script first runs it against the original cube bounds
and requires a real test failure, then restores the patch and runs the core
library suite, formatting, Clippy and server build under the shared lock and
resource limits. The negative regression failed as expected; 470 core library
tests, workspace formatting, core all-targets/all-features Clippy and the debug
server build passed. Fixture hashes, identical stimulus commands, copied binary
hash and final source hashes were verified.

Upstream master 998c3f8 retains the spherical selection. Open PRs 3407 and
3661 concern dragon parts; 3663 concerns creeper cloud creation and 3816 water
potions. Their inspected patches do not implement this contact-volume fix.
Fork master 65bca3f is already an ancestor of this branch. Evidence remains
local under `artifacts/christine-dragon34-*`; no logs, jars, worlds or decompiled
Java are committed.

## Limits

This is server-state evidence from headless clients. Rendered particles, a
complete dragon fight, natural End landings and lingering-potion gameplay are
not proven. Cloud effect eligibility, five-tick application cadence, owner
attribution and timed-effect strength/duration remain independent leads.
