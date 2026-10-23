# Wither pursuit route retention

A powered Wither pursuing a level target drifts upward after several ticks on
campaign 90. In the repeated isolated arena, official Java 26.3 reaches
Y=100.600496 at tick 5; Pumpkin reaches Y=100.624496 and keeps climbing. The
near-level case separates at tick 7. The existing eight-tick flight fixture
reproduces 12 vertical-motion failures across both trials, while descending,
spawn-charge and NoAI controls pass. Official passes all 315 checks; baseline
passes 303/315. Commands and fixture match between targets.

Vanilla WitherBoss uses RangedAttackGoal, FlyingPathNavigation and
FlyingMoveControl. The ranged goal requests navigation every tick while outside
shooting range. PathNavigation.createPath returns the current unfinished path
when its target block is unchanged. Campaign set_progress instead discards it
on each request. Once the boss passes a half-block height, rebuilding from the
rounded flying start node changes its vertical waypoint and input direction.

The correction preserves an unfinished path only while its target block matches
the new request. It retains node progress and the stuck timeout, while updating
speed, goal and the last stuck-check position. Completed routes and changed
target blocks still clear the path and timeout before the next search, including
when a previous search cooldown is nonzero. Sub-block target movement reuses the
route, matching vanilla's block-position comparison.

This is an attributed narrow adaptation of route retention from
[callowaysutton's PR #3955](https://github.com/Pumpkin-MC/Pumpkin/pull/3955),
head `20dc1d0ed53501a3b750759514da6028a22217c6`. The shared search budget and
terrain caches are excluded. Current upstream has already moved to pending-path
installation and same-target reuse through the merged AI foundation. This is a
correction to the retained campaign architecture, not a new upstream bug claim.
Fetched fork master is already an ancestor; no branch history is rewritten.

The shared set_progress entry point also serves ground, swimming, amphibious
and climbing navigation through movement, combat, following, fleeing, roaming,
breeding, temptation, item collection, trading and raid goals. Those callers now
retain unfinished routes when the path target equals the requested block.
Ground destinations normalized to another surface block keep their previous
invalidation behavior. No caller signature or navigation-stop behavior changes.
General dynamic-terrain and other-mob gameplay are not established by this
Wither reproduction.

Two focused Rust tests cover repeated same-block requests and timeout retention,
plus completed routes and target changes on all three axes. The retention test
fails on the original source with no path instead of next-node index 1; the
completed/retargeted controls pass there. Runtime regression uses the existing
fixtures/wither-level-flight/cases.json and captured official vertical-motion
oracle with the unchanged checker. No new Python infrastructure is introduced.

Workspace formatting, all 454 core Rust library tests, core all-target/all-feature
Clippy and the debug server build pass under the shared Cargo lock, one build
job and the prescribed resource caps. The existing proc-macro-error2
future-compatibility warning remains. The first formatting check found only
assertion wrapping; it was corrected before the passing final checks.

The identical patched arena run passes all 315/315 checks, matching official
315/315 and resolving the baseline's 12 failures. Five cases run twice with
eight sampled ticks each, advancing 356 controlled ticks per target. Vertical
position and velocity match within 1e-6, effective gravity transitions and
health/phase match, the observer and actors remain present, cleanup and shutdown
succeed, and successful server logs contain no errors. Deployment-only manifests
verify identical probe, fixture and gameplay commands, plus source, binary,
official jar, oracle, checker, packet, log and client hashes. Raw logs, worlds,
binaries and decompiled Java stay outside the repository.

The arena uses a real headless protocol-777 observer, not a rendered client.
Whole-fight, Bedrock, arbitrary obstacles, fluids, horizontal motion and turning
remain unverified. A human can check an isolated powered Wither pursuing a
resistant target at the same height; expect it to settle back down after the
initial rise rather than repeatedly selecting higher waypoints. Capture a
side-by-side recording with vanilla before any upstream submission.
