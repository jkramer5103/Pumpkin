# Wither construction destruction effects

Building a Wither consumed skulls, soul sand and soul soil using particle-only
level events whose payload always identified soul sand. The official 26.3 server
uses particles-and-sound destruction events, with each consumed block's original
state ID. This affects the block fragments and break sounds during construction.

`WitherSkullBlock.checkSpawn` delegates clearing to
`CarvedPumpkinBlock.clearPatternBlocks`. Its event 2001 carries the state cached by
`BlockInWorld.getState` during pattern matching, even though the event follows
replacement with air. The Rust construction path now snapshots the seven consumed
states before clearing and uses the existing `ParticlesAndSoundDestroyBlock`
event. Structure recognition, advancement dispatch and boss initialization retain
their existing behavior.

The focused fixture summons from sand, soil and mixed bases, using both structure
axes and a dispenser for the final skull, twice each. An exact protocol 777
headless observer captures event type, block position and numeric state payload.
The checker requires each of the seven consumed positions to match vanilla's
payload and sound event, with spawn, Invul, cleared-block, tick and client controls.
The final dispenser skull also exercises a different state from the default
standing skull. Unsupported block-state setup syntax in preliminary discovery
runs was removed; those failed runs are excluded from final evidence.

All 446 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and a debug server build passed under the shared Cargo lock and resource
limits. The existing `proc-macro-error2` future-compatibility notice remains.
The same eight arena cases pass 160/160 checks on vanilla and patched Pumpkin.
Baseline Pumpkin passes 112/160, failing exactly eight sound-event checks and
40 consumed-state payload checks. Each target received identical command hashes
and 248 controlled ticks. Source, copied-binary and fixture hashes, cleanup,
process stops and clean server/client logs were verified. The normal regression
checker rejects the baseline. Coverage is the world fixture/report checker;
no mocked Rust getter test was added.

Live before/after proof uses campaign commit `5f94699f5` as its baseline, rather
than a separate upstream-master build. Raw reports, official jar/decompiled
references, source/binary hashes and one-off investigation tools remain outside
the repository.
This change does not establish full Wither parity. Vanilla also emits events for
the two air pattern cells and clears in a different order; those separate
construction-order/neighbor-update differences are not corrected here.

Rendered-client check: build a Wither with mixed soul sand and soul soil and
confirm the consumed skulls and soul blocks produce their own block fragments
and break sounds. Capture a recording of the final skull placement and startup.
No rendered-client, Bedrock or whole-fight proof is claimed.

Fork master was fetched and is already an ancestor. Refreshed upstream master
`44d881c32` retains the same particle-only, soul-sand-payload construction path;
its newer unrelated commits were not merged. Open Wither/skull/summoning searches
and PR3507/3835/4092/4107 file reviews found no overlapping construction patch.
The [tracker](https://pumpkinmc.org/tracker/) and
[Mob AI issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) remain leads;
the spawn-window goal was already fixed and was not repeated.
