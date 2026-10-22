# Wither skull initial launch speed

Assignment 76, lane jaron (Christine subscription only). Source baseline
`5c4fedff2f9e720ee63adc27731249fa9fc0c53e`.

A Wither launches a skull at speed 0.95 in Pumpkin, versus 0.1 in vanilla
26.3. This is the initial velocity at the firing head, before the skull's first
flight tick. The skull constructor now uses the existing
`INITIAL_ACCELERATION_POWER` constant shared with the other hurting projectiles.
This changes ordinary and dangerous shots through their common constructor.

Vanilla `WitherBoss.performRangedAttack` normalizes the aiming direction and
constructs `WitherSkull`, which delegates through `AbstractHurtingProjectile`.
That constructor calls `assignDirectionalMovement` with the default acceleration
power 0.1; it normalizes the direction and sets velocity to that vector times
0.1. A zero direction stays zero. Decompiled vanilla is kept outside the repo.

Current upstream retains the 0.95 launch speed. Fork master is an ancestor of
this branch and has no new entity fixes to integrate. Tracker and Mob AI issue
3468 were checked; the spawn-window goal was fixed earlier in the campaign.
Open PR 3835 changes flight/collision and skull damage, but leaves the skull
constructor's launch speed unchanged. PR 4092 covers shared movement foundations;
installing a flying controller without its navigation integration is deferred.
No shared navigation, collision or damage changes are included here.

The focused fixture `fixtures/wither-skull-launch-speed/cases.json` defines
positive/negative X, positive Z, an upward 3:4 diagonal, and a coincident target,
twice each. A creative headless protocol-777 observer keeps a loaded scratch
arena ticking. Before each single tick, reset the boss position and velocity
and remove old skulls. Read a natural main-head shot's `Pos` and `Motion` while
it remains exactly at the head `(15,83,15)`. This excludes velocity decay from
a flight tick. Health, target survival, observer mode, command errors, cleanup,
verified ticks and stopped processes are controls. The zero case protects the
stationary-shot behavior independently of the speed correction.

Run the focused report check with:

```
python3 tools/parity-lab/tests/check_wither_skull_launch_speed.py REPORT.json
python3 tools/parity-lab/tests/check_wither_skull_launch_speed.py BASELINE.json --baseline
```

Vanilla and patched Pumpkin each passed all 80 focused checks. The campaign75
baseline passed 72/80, failing exactly the eight nonzero launch-motion checks
(four directions, twice). Both zero-motion controls and all origins, health,
observer, command-error, cleanup and stopped-process controls passed. Every
shot was observed at tick41, at the exact firing origin. Each target advanced
686 controlled ticks. Stimulus commands match across all three targets after
excluding only game-time polling. Source, copied-binary, fixture, probe, checker
and report hashes were verified; server and client logs contain only the known
debug/development and offline-server startup warnings.

Workspace formatting, all 450 core Rust library tests, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock with one
job, disabled debug info/incremental compilation, 5GiB memory, no swap and 200%
CPU quota. The existing `proc-macro-error2` future-compatibility notice remains.
The initial validation stopped before compilation because free disk space was
below 6GiB. Older stopped Jaron scratch binaries were compressed and verified
against their original SHA256 hashes; the successful retry started with over
8GiB free. No unrelated caches or build targets were removed.

Detailed private evidence is in `artifacts/jaron-wither76-live-validation.json`,
`artifacts/jaron-wither76-verify.json` and the source-provenance/completion records.
The Rust source SHA256 is
`f01621795688fabd262ffb722f154b5bce59d49b6a497a741e1f56d0bb364dda`;
the validated debug binary SHA256 is
`66dc7be791d37b2d48bd186560fcf2d085894e03dce909bb378a4a3427842f0c`.

Limits: this proves initial velocity only. Subsequent acceleration, drag,
water inertia, collision, skull damage/effect attribution, spawn rotation and
whole-fight behavior remain separate work. The existing thrown-projectile flight
still lacks vanilla hurting-projectile acceleration; matching launch speed does
not establish the subsequent trajectory. No separate upstream-master binary
was tested. The arena directly exercises ordinary main-head launches; dangerous
and side-head shots use the same constructor but are not directly measured here.
No rendered-client or Bedrock proof is claimed. For a human check, record a
Wither's newly emitted skull beside a stationary target in a disposable arena,
comparing its initial motion with vanilla; no recording has been made.
