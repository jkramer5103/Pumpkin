# Wither spawn-window goal

Pumpkin's idle goals could turn a Wither's main head while spawn invulnerability
was active. Vanilla reserves looking during that window. The Wither now
registers `WitherDoNothingGoal` at priority zero, reserving MOVE, JUMP and LOOK
while `Invul > 0`. The same condition determines continuation. Other goals can
run outside the spawn window. A weak reference avoids a boss/selector ownership
cycle; no shared entity, movement, combat or goal-selector code changes.

Reference: vanilla 26.3 `WitherBoss.registerGoals`, its inner
`WitherDoNothingGoal`, base `Goal.canContinueToUse`, and selector scheduling.
The [mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468)
and [parity tracker](https://pumpkinmc.org/tracker/) supplied leads. Fresh open
Wither PR checks found separate work: 3865 (death drops), 4038 (effect immunity),
3835 (projectiles) and 3793 (touch/velocity). Fork master
`65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor; upstream
master remains `5b53f064af8708ba33fcaa533b81ca29a53a3310`.

Focused fixtures: `wither-spawn-look-suppression.json` and
`wither-active-look-control.json`. Each uses four Withers near a creative player,
180 verified ticks, a floor, and position/velocity resets every ten ticks.
The first starts at `Invul:200` and stays inside the spawn window; the second
starts without invulnerability. Command observations verify all four boss
positions and invulnerability counters, plus player presence. A task-local
exact protocol 777 client records added Wither entity IDs and their decoded
`ClientboundRotateHeadPacket` values. Spawn requires no nonzero head yaw;
the ordinary active control requires at least one. The command fixtures alone
do not assert head yaw. Bot scripts, raw logs, worlds and decompiled Java stay
outside Git.

Rust validation passed under the shared Cargo lock, one build job and required
memory/CPU limits: 443 core library tests, workspace formatting, core
all-targets/all-features clippy, and a full Pumpkin binary build. Evidence:
`artifacts/jaron-wither-spawn-verify.json` and build log in the live lab.

Final comparison repeated both fixtures twice on each target:

| Target | Nonzero spawn head-yaw packets, trials 1 / 2 | Active head-yaw packets, trials 1 / 2 | Checks |
| --- | --- | --- | --- |
| Baseline `79bf6c1` | 277 / 179 | 242 / 296 | 58/60; only both spawn assertions fail |
| Vanilla 26.3 | 0 / 0 | 138 / 87 | 60/60 |
| Patched Pumpkin | 0 / 0 | 350 / 301 | 60/60 |

Fixture hashes match across targets. All six scratch servers stopped, with no
ERROR or panic lines. The patched binary SHA-256 is
`db04634e9ccc91d76d0b1134431375ceb3c722e1cda153123617b81c9edb3217`.
Final evidence index: `artifacts/jaron-wither-spawn-completion.json` in the live
lab; it records raw report paths, fixture/binary hashes and exact assertions.

Earlier setup failures are preserved and excluded: whitelist rejection,
teleport-client disconnects and unpinned vanilla drift. An exploratory pitch
counter stayed at zero on Pumpkin despite head-yaw changes. Pitch is a separate
field, and final regression assertions use head-yaw packets directly. No generic
Python infrastructure changes or investigation tools are published.

Limits: these are server-state and headless protocol observations, not human
visual proof or a full boss fight. MOVE/JUMP reservations match vanilla source
but are not independently exercised here. Goal release during an expiring spawn
window, full movement, pitch alignment, attack timing and other missing Wither
AI remain separate work.
