# Wither construction neighbor notifications

Assignment 68 corrects the neighbor notifications from successful Wither
construction. A quasi-connected dispenser beneath either air gap under the arms
must receive an update and dispense an item. Pumpkin left that dispenser dormant:
its clearing loop notified neighbors only when an occupied cell changed to air,
so it never notified the block below an already empty pattern cell.

The Rust construction path now clears the pattern with `NOTIFY_LISTENERS`, then
calls `update_neighbors_at` with air for all nine pattern cells after inserting
the Wither. The official 26.3 `WitherSkullBlock.checkSpawn` calls
`CarvedPumpkinBlock.clearPatternBlocks` with flag 2 and subsequently calls
`updatePatternBlocks` after `addFreshEntity`. The latter loops over all pattern
cells and calls `updateNeighborsAt` with air, even for unchanged air cells.
Vanilla's `DispenserBlock.neighborChanged` checks for power at both its position
and the position above it. Pumpkin's existing dispenser behavior does the same;
it needs the construction notification to wake up.

The source change is confined to `block/blocks/wither_skull.rs`. Shape updates
still use the existing world path. Cached destruction-event states and order,
boss initialization, advancement dispatch and failed constructions retain their
existing paths. No shared world, combat or dispenser implementation changes.

The focused world fixture repeats five cases twice: dispensers under both X-axis
air gaps and the negative Z-axis gap, plus unpowered and incomplete-construction
controls. Each dispenser starts with two stones. Successful powered construction
must change its trigger state and eject exactly one stone; the controls must keep
both stones. A subsequent ordinary adjacent block update also exercises the
same dispenser circuit, proving that dormant baseline dispensers can activate.
The fixture checks actual construction through a powered skull dispenser,
cleared blocks, invulnerability, client connection, controlled ticks and cleanup.
The report checker compares observations with these vanilla outcomes and rejects
the baseline without the correction.

Validation passed: 446 `pumpkin-core` library tests, workspace formatting, core
all-target/all-feature Clippy and a debug server build under the shared Cargo
lock and resource limits. The same ten-case arena passes 126/126 checks on
vanilla and patched Pumpkin. Baseline campaign `461d97c96` passes 108/126,
failing exactly the eighteen trigger, inventory and ejected-item observations
for successful powered constructions. Its ordinary dispenser controls pass.
The normal regression checker rejects that actual baseline result.

All targets received identical command hashes and 490 controlled ticks. Source,
copied-binary and fixture hashes, cleanup, process stops and clean server/client
logs were verified. The initial formatting check requested line wrapping and
stopped before compilation; after correction all Rust checks passed. The existing
`proc-macro-error2` future-compatibility notice remains.

The fixture provides focused world regression coverage; no mocked Rust flag test
is added. No client rendering, audible recording, Bedrock behavior or whole-fight
parity is established by these headless protocol-777/server-state checks. The
baseline is a campaign binary, rather than a separately built upstream-master
binary. The Z-axis positive gap and notification timing relative to entity
insertion were not independently observed; their implementation follows the
official call sequence.

Fork master `65bca3f7f` is already an ancestor. Refreshed upstream master
`44d881c32` has the same missing notification pass. Open Wither/construction/
neighbor PR searches and relevant file reviews found no construction overlap.
Mob AI, projectile, death/drop and explosion foundations covered by existing
upstream PRs remain deferred. The [tracker](https://pumpkinmc.org/tracker/) and
[Mob AI issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) supplied leads;
the previously completed spawn-window goal fix is not repeated.

A human can build a normal Wither over a dormant quasi-connected dispenser
under an arm, using a redstone block diagonally above the dispenser. Complete the
skull row and expect one stone to dispense. Repeat without the redstone block
and expect no dispensing. Record the final skull placement and item ejection
for a visual check; no rendered client capture is claimed here.
