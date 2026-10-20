# Wither construction clearing order

Assignment 67 corrects the order in which a successful upright Wither construction
clears its pattern and emits block destruction events. Pumpkin processed seven
occupied cells, starting with the middle skull. Official 26.3 processes all nine
cells, visiting each column top to bottom, including the two air cells under
the arms. The first column is the negative-axis end when that end skull completes
the structure; otherwise it is the positive-axis end.

The Rust pattern now retains those nine positions in the matched reference order.
The existing cached-state destruction loop consumes them directly, preserving
the previous fix for event kind and original block-state payloads. Pattern matching, spawn
position, boss orientation, invulnerability and advancement handling keep their
existing paths. No shared entity, combat or world code changes.

Reference: the official 26.3 `WitherSkullBlock.checkSpawn` calls
`CarvedPumpkinBlock.clearPatternBlocks`. That helper loops width before height,
calls `setBlock` and emits event 2001 for every cell. The official block pattern
is three columns of skull, soul block, then air/soul block/air. `BlockPattern.find`
searches a cube from the placed skull toward positive coordinates, which determines
the first matching column. The local official jar, decompiled Wither source and
`javap` evidence remain outside the repository.

The regression fixture covers each of the three final-skull positions on the
X axis and the positive-end skull on the Z axis, repeated twice in isolated,
frozen arenas. It checks the complete ordered position/state event sequence,
actual construction through a powered dispenser, successful spawn,
invulnerability timer, cleared blocks,
client connection and cleanup. The normal checker rejects the baseline and accepts the official server and
the patched candidate.

Validation passed: 446 `pumpkin-core` library tests, workspace formatting, core
all-target/all-feature Clippy and a debug server build under the shared Cargo
lock and resource limits. The same eight-case arena passes 104/104 checks on
vanilla and patched Pumpkin. Baseline campaign `73afc8c13` passes 96/104, failing
exactly the eight clearing-sequence checks. Each target received identical command
hashes and 248 controlled ticks. Source, copied-binary and fixture hashes,
cleanup, process stops and clean server/client logs were verified. The existing
`proc-macro-error2` future-compatibility notice remains. This is not a separate
upstream-master binary comparison.

The fixture and checker provide focused world regression coverage; no mocked
Rust pattern getter test is added. The initial arena attempt misplaced
a Z-axis dispenser; a second broader attempt used a dispenser-facing property
that Pumpkin commands do not support. Both attempts are excluded. The second
official run also exposed the final-skull-dependent column direction, which is
covered by the corrected source and fixture. Negative/middle Z completions remain
untested on Pumpkin because that setup requires a nondefault dispenser facing.

Fork master is already an ancestor. Refreshed upstream master `44d881c32` still
uses the seven-cell clearing list. Wither and construction-specific open-PR
searches plus PR3507/3835/4092/4107 file reviews found no overlapping construction
patch. The [tracker](https://pumpkinmc.org/tracker/) and
[Mob AI issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) are leads;
the spawn-window goal was previously completed and is not repeated here.

This bounded correction does not establish whole-fight parity. Deferred neighbor
notifications after boss insertion remain a separate candidate, requiring a
reproducible adjacent-block or redstone outcome before selection. Headless packet
observations do not prove rendered particles or audible sound behavior. A human
can record the final skull placement on mixed soul-sand/soil structures in both
orientations to check the visible and audible destruction sequence.
