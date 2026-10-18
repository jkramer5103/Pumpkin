# Dragon flight history at startup

Newborn dragons kept zero-height and zero-yaw samples in their delayed flight
history. At y100, the mismatch between samples five and ten ticks ago tilted the
head by 1000 degrees during startup. A directly breathing dragon emitted its
cloud near z=-3.1287 instead of z=-8.5. This changed which entities took damage.

`DragonFlightHistory::record` now initializes every retained sample from the
first observed height and yaw, as vanilla 26.3 does. Subsequent records retain
the existing 64-sample ring behavior. No shared entity/combat files change.

The Rust regression covers initial delayed samples, the next observation, and
ring rollover. The initial-sample regression is also run against the unchanged
baseline implementation and must fail before the patched crate checks run.

## Comparison

The permanent `dragon-flight-history-startup.json` scenario runs two trials of
newborn phase-5 dragons at y100 facing north, y80 facing east, and a paused NoAI
dragon resumed before its first observation. Each case checks emission after
exactly ten active ticks, the cloud position, and damage to sheep at the proper
and formerly distorted locations. The dragon is paused and moved away after
emission to isolate cloud damage from dragon contact. Targets use isolated,
loaded overworld arenas and a connected headless protocol client. The final
fixture advances the arena for 40 ticks before spawning the first dragon;
newborn histories still begin with their first active dragon tick. All dragon,
cloud and victim positions fit inside the existing seeded chunk; platform
blocks are checked before and after each emission.

469 core library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared Cargo lock and
resource limits. The baseline initial-history regression failed as expected.
Final identical-fixture comparison: vanilla and patched Pumpkin passed 66/66
checks each; baseline passed 48/66, failing exactly the six cloud positions and
twelve corresponding victim checks. All platform checks and tick deltas passed
on all targets (290 controlled ticks each). All scratch processes stopped;
both Pumpkin saves completed. Logs contain no errors or panics. Vanilla final
save completion was not confirmed within the harness shutdown grace period.
Reference, baseline and patched evidence remains local under
`artifacts/christine-dragon33-*`; raw logs, worlds, binaries and decompiled Java
are excluded from this commit.

## Limits

This checks startup history and an observable downstream damage footprint. It
does not validate a complete dragon fight, flight paths, rendered multipart
geometry or a natural End landing. There is no rendered-client capture.
Earlier scratch runs outside the seeded chunk exposed inconsistent terrain and
victim state. The initial patched and diagnostic runs each passed 52/53 checks,
with different victim checks failing. A prewarmed run passed 52/54: the first
cloud had the correct horizontal position but landed at y64 rather than the
constructed y80 platform. Later cases used y80. These reports remain retained,
and do not count as full passes. The final scenario keeps all tested entities
inside the existing seeded chunk and verifies its platform. The source fix does
not change chunk loading or entity lifecycle; the cause of the earlier victim
disappearance remains unproven.

Multipart registration/damage work in upstream PRs 3407 and 3661 is independent;
those patches and PR 3835 do not initialize flight history.
