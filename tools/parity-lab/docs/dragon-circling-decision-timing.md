# Dragon circling phase decision timing

Pumpkin could abandon an unfinished circling leg to land or strafe because it
rolled for a phase change every tick. Vanilla DragonHoldingPatternPhase.doServerTick
only calls findNewTarget at its distance/collision boundary, and findNewTarget
only considers another phase when an existing path is done.

The Rust correction snapshots that eligibility before consuming or generating a
waypoint. A missing initial target, remaining path nodes, or a distant unreached
target prevents a phase change. The focused Rust regressions cover these states,
the exact distance boundaries, and horizontal collision. Only the dragon's
circling file changes; no shared entity, combat or world code is reserved.

Reference: locally decompiled Minecraft Java 26.3 DragonHoldingPatternPhase,
EnderDragon.aiStep, and EnderDragonPhaseManager.setPhase. The official
[parity tracker](https://pumpkinmc.org/tracker/) and
[Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) are
leads, not behavioral proof. Fork master is already integrated. Fresh upstream
source and open dragon/holding-pattern/path PR searches show no equivalent timing
fix. PR3407/3661 concern multipart behavior and PR3835 concerns projectiles; their
remaining work is excluded from this patch.

The focused fixture is
[dragon-circling-decision-timing.json](../lab/examples/dragon-circling-decision-timing.json),
with captured results checked by
[check_dragon_circling_decision_timing.py](../tests/check_dragon_circling_decision_timing.py).
It creates an isolated flat overworld with a connected headless protocol client.
Eight dragons are separated by 28 blocks at Y180. One hovering tick initializes
the nodes before circling is selected, excluding the separate initial random-route
lead. Every eight ticks their position and motion are reset to keep flight
waypoints distant without resetting their phase or path. All eight must remain
present and circling at each of 32 samples across 256 flight ticks. An initial
phase assertion, a stationary NoAI control, and a hovering phase/altitude control
are included. Total controlled time is 297 ticks per server.

All 489 core Rust library tests, workspace formatting, core all-targets/all-features
Clippy and a debug server build passed under the shared Cargo lock and resource
limits. Both focused regressions fail with unconditional per-tick phase eligibility
restored, then pass with the correction. Only the existing proc-macro-error2
future-compatibility warning remains; temporary negative-control unused-variable
warnings do not apply to corrected source.

The final fixture passes 105/105 checks on vanilla. Baseline Pumpkin passes
73/105, with exactly 32 expected circling-retention failures and no other failed
controls. Patched Pumpkin passes 105/105 with all eight dragons circling in every
sample, matching vanilla. Source, copied-binary, fixture and stimulus hashes match
the validation records. All scratch servers stopped, both Pumpkin saves completed,
and server/client logs contain no errors or panics. Vanilla final-save completion
was not confirmed within the shutdown grace period. Phase-change counts on baseline
are random; reproducing at least one premature phase change is required rather
than a particular random count. All targets receive the identical fixture.
Numeric NoAI position and hovering altitude controls avoid SNBT float-display
differences (`230d` versus `230.0d`). Captured comparison artifacts and exact
source/binary hashes stay outside Git.

Limitations: headless protocol and server-state evidence only; no rendered client
capture, natural complete orbit, crystal-present End fight or whole-fight proof.
The existing phase-choice probabilities, player eligibility, extra FlyToPortal
phase, initial random routing and vertical-collision support need separate
reproduction and correction. This patch only fixes when phase changes are allowed.
Graph float/tie and unreachable-path behavior are also separate unconfirmed leads.
Multipart/crystal healing/despawn/projectile work remains deferred to the open PRs.

Manual follow-up: join an isolated End arena with a real client, watch dragons
finish circling legs before choosing another phase, and record the transitions.
A rendered-client recording and a natural complete fight remain unverified.
