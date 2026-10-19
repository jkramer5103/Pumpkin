# Wither construction arm clearance

Pumpkin accepted a soul-block T even when either space beside the bottom
stem was occupied. Vanilla 26.3 requires air in both spaces before the final
skull can summon the boss. Invalid structures must remain intact.

The correction checks both lower corners in `find_wither_pattern`, using
`BlockState::is_air` so cave and void air retain their vanilla meaning. It
leaves the existing skull matching, spawn phase and callbacks in place.

Vanilla reference: `WitherSkullBlock.getOrCreateWitherFull` builds the pattern
`^^^ / ### / ~#~`, with `~` matched by `BlockState.isAir`. Current upstream
master has the same missing checks as the fork baseline. Fork master was
already an ancestor of this lane. Open Wither/skull/soul PR searches and
relevant PR file lists showed no equivalent correction to this block file.
Existing flight, targeting, skull flight and death/drop proposals remain deferred.

Focused regression coverage is the construction fixture, exercised against real
scratch worlds rather than an artificial World mock. Its driver sends a protocol
777 `UseItemOn` packet at each `PARITY_BUILD_PLACE` marker: vanilla console
`setblock` alone does not invoke the final skull's player placement callback.
The test checks boss presence, remaining base/skull blocks and boss spawn packets.
It uses both horizontal axes, ordinary/cave air positive controls, a stone block
in either corner, a filled soul-sand bottom row and water in one corner.

Rust verification passed under the shared Cargo lock and required resource
limits: workspace formatting, all 444 `pumpkin-core` library tests, core Clippy
with all targets/features, and the debug server build. The existing
`proc-macro-error2` future-compatibility warning remains.

The same fixture ran twice in each scratch world. Vanilla passed 248/248
checks; the pre-fix binary passed 184/248, with exactly 64 expected failures
for incorrect boss spawning, consumed base/skull blocks and spawn packets
in blocked-corner cases. The patched binary passed 248/248 checks, matching
vanilla. Each target advances 673 controlled ticks including cleanup. Fixture, gameplay-command,
source and copied-binary hashes match in the local evidence. All three scratch
processes stopped and arena cleanup passed. Both Pumpkin saves completed;
final server/client logs contain no ERROR, panic or uncaught-thread-exception
lines. Vanilla final-save completion was not verified within shutdown grace.

The initial Pumpkin probes could not place the final skull because their
client setup lacked loaded notifications and/or operator bypass for scratch
spawn protection. They are excluded. Final runs send the notification before
each placement and use the same operator setup on all targets.

This is headless protocol and server-state coverage; no rendered-client,
complete spawn explosion/fight, Bedrock, reload or plugin-listener proof is
claimed. The focused world regression is retained as a scenario fixture;
no new isolated Rust unit test was added.

Separate construction leads remain: Peaceful gating, initial position/rotation,
wall skulls, and summon-base block tags. They are outside this bounded fix and
require their own reproduction and overlap review.
