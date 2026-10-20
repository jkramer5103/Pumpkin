# Wither skull aiming at close targets

Assignment 63, lane jaron (Christine subscription only). Source baseline
`af5a16a320c7acc2c2ecf2c39674893f08b025ab`.

A Wither aiming at a target within 0.001 blocks of its firing head substituted
positive Z for the actual direction. Vanilla 26.3 `WitherBoss.performRangedAttack`
passes `direction.normalize()` to `WitherSkull`. `Vec3.normalize` returns zero
below `1.0E-5F` (widened to double), and otherwise divides by length.
`WitherSkull` delegates through `AbstractHurtingProjectile` to a second
normalization. Zero therefore stays zero, while a vector such as
`(0.0005,0,0)` keeps its positive-X direction. The boss now applies that same
normalization. This private helper has one production caller and covers main,
side and random skull aiming. Shared vector normalization and projectile speed,
flight, collision and damage attribution are outside this correction.

The Rust regressions cover positive/negative close shots, an ordinary shot,
zero/sub-epsilon vectors, and the exact float-widening boundary. Restoring the
old normalization makes both regressions fail.

The scratch-world fixture in `fixtures/wither-skull-aim/cases.json` positions a
NoAI villager with Resistance V so its half-eye target is next to the main head
at `(15,83,15)`. A creative protocol-777 observer keeps the arena ticking. Before
each single tick, teleport the Wither to `(15,80,15)`, clear its motion and remove
old skulls. Capture `Pos` and `Motion` of the newly launched main-head skull;
each final case fires on tick 41. Run six offsets twice: +/-0.0005, coincident,
0.000005, 0.00002 and the 0.005 control. The comparison asserts direction and
zero motion, not speed: vanilla's launch speed is 0.1 and the existing Pumpkin
projectile constructor uses 0.95. Projectile flight remains deferred to upstream
PR3835.

Validate an arena report with:

```
python3 tools/parity-lab/tests/check_wither_skull_aim.py REPORT.json
python3 tools/parity-lab/tests/check_wither_skull_aim.py BASELINE.json --baseline
```

The local probe and source/build/evidence reports are under
`/root/pumpkin-parity-lab/artifacts/jaron-wither63-*`. Initial discovery used
integer coordinates (centered by vanilla) and an untargetable invulnerable
villager; those runs do not establish the bug and are excluded. Corrected
four-case discovery established vanilla +/-X and zero motion versus baseline
positive Z, with the ordinary control agreeing in direction. Final validation
uses the same six-case fixture on all three targets. One initial repeated
baseline run missed a shot observation and is excluded; the rerun waits 50 ms
after advancing each frozen tick before reading entities. This changes no
commands or controlled ticks. The final vanilla and baseline command sequences
match after removing only game-time polling queries.

The final before comparison passed 96/96 checks on vanilla and 86/96 on
baseline Pumpkin, with exactly ten aiming failures (five offsets, twice), and
all ordinary-shot, origin, health and observer controls passing. Each target
advanced 818 controlled ticks, including cleanup. Server and client logs had no
panic, exception, fatal or error lines. Patched Pumpkin passed all 96 checks
with the same 818 controlled ticks and command sequences. Its close +/-X shots aim toward the target, sub-epsilon and
coincident shots have zero motion, and the ordinary-distance controls still
pass. Binary, source and fixture hashes match; cleanup, process termination and
clean client/server logs also pass.

| Target | Passed checks | Aiming failures | Controlled ticks |
| --- | ---: | ---: | ---: |
| Vanilla 26.3 | 96/96 | 0 | 818 |
| Baseline Pumpkin | 86/96 | 10 | 818 |
| Patched Pumpkin | 96/96 | 0 | 818 |

All 446 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock with one
build job, no debug information or incremental compilation, 5 GiB memory,
zero swap and 200% CPU limits. Both regressions failed when the old aiming logic
was restored. The pre-existing proc-macro-error2 future-compatibility notice
remains. The source hash and copied binary hash are recorded in the build report.

PR3835 changes projectile flight/context, while PR4092 changes Wither movement
and bossbar foundations. Neither changes this boss aiming fallback. Tracking
issue 3468's invulnerability-window goal is already implemented by an earlier
campaign patch. Fork master is an ancestor of the campaign branch; there are no
new master fixes to integrate.

Limitations: command-positioned main-head attacks in a scratch arena, default
scale and headless protocol observation. Side/random heads share the corrected
helper but have no direct close-target arena proof. No rendered-client, Bedrock,
natural fight or whole-boss parity proof is claimed. For a visual check, arrange
a stationary target's half-eye position next to a Wither firing head and record
the launch: close +/-X shots should point toward that target, and coincident
shots should begin with zero motion. No real-client recording has been made.
