# Dragon respawn pillar clearing

Dragon respawn must clear the entire inclusive 21-block cube around each pillar
cap before the explosion and pillar feature run. Pumpkin excluded obsidian and
bedrock, leaving player-built blocks outside the rebuilt pillar footprint.
The Rust correction removes those exemptions and uses the existing block-position
iterator and fluid-state helper to match vanilla removal.

Official 26.3 `DragonRespawnStage.SUMMONING_PILLARS` calls
`Level.removeBlock(pos, false)` for every position from center/height minus ten
to plus ten. `removeBlock` replaces the block with its contained fluid using
notification flags 3. It has no explosion-resistance or dragon-immunity gate.
The subsequent explosion, column regeneration, cap and crystal remain in order.
The iterator visits X first, like vanilla `BlockPos.betweenClosed`.

The focused fixture and `check_dragon_respawn_pillar_clearing.py` validate an
isolated actual respawn ritual started by an end-crystal item-use packet from a
headless protocol 777 player after killing the initial fight dragon. Two pillars
each receive thirteen verified markers: obsidian/bedrock above the feature's
footprint and at four inclusive cube corners, an ordinary-stone control, and
six markers one block outside each cube face. Pillar heights/radii and podium
height are discovered independently on each server.

Before-fix evidence: official 26.3 passes all 26 expected block samples;
campaign 73 leaves exactly twelve obsidian/bedrock markers uncleared. Both
ordinary-stone controls and all twelve preservation controls pass. Both targets
pass actual item-use, regenerated cap/crystal, exactly 185 observation ticks,
untouched third-pillar, connected player/client, abort, cleanup and stopped
scratch-server controls. Source/binary provenance is recorded in campaign
artifacts. No separate upstream-master binary was run.

`cargo fmt --all -- --check`, all 493 `pumpkin-core` library tests,
`cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
`cargo build --locked -p pumpkin` passed under the shared Cargo lock with one
build job, debug information and incremental compilation disabled, and the
required memory/CPU limits. Only the existing `proc-macro-error2` future-
compatibility notice remains. The patched binary passes all 26 sampled blocks,
matching official 26.3, including all preservation and ordinary-stone controls.
All three targets pass the actual item-use, regenerated caps/crystals, exact
185 observation ticks, untouched third pillar, player/client, cleanup and stopped-
process checks. Six server/client logs contain only known startup warnings and
no errors. Source, binary, fixture, checker, probe, packet and log hashes were
verified and recorded in the campaign artifacts. The live regression exercises
real block updates; no constructor-only or mocked-world Rust test was added.

Upstream master `9c04f714bb7eb26579c652f9744895d465ee902b` retains the exemptions.
Read-only open-PR searches found no spike/pillar clearing fix. PRs 3694, 3407 and
3661 cover crystal combat, dragon hitboxes or fight tracking without changing
this clearing loop. The fork master is an ancestor of this campaign branch;
existing relevant campaign patches are retained.

This bounded check covers two pillars and selected solid-block boundaries. It
does not prove a whole fight, completed ritual, rendered-client appearance,
Bedrock, chunk reloads, custom dimensions, all cage properties or fluid behavior.
Fluid retention follows vanilla and the existing world helper but has no direct
arena sample here. For a real-client check, place obsidian/bedrock beside a pillar
top outside its radius, start the respawn ritual, and observe those blocks removed
as that pillar regenerates; blocks beyond the ten-block cube must remain.
