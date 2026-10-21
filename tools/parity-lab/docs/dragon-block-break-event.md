# Ender Dragon block destruction particles

The dragon removed breakable blocks without notifying clients of the dragon's
block destruction particle effect. Vanilla 26.3 `EnderDragon.checkWalls` records
whether any `removeBlock` succeeds, then emits level event 2008 with data zero at
a uniformly selected integer position within that scan's inclusive bounds.
It emits once per successful part scan, rather than once per block or per tick.

The Rust correction accumulates successful replacements in `check_walls` and
sends the generated `WorldEvent::ParticlesDragonBlockBreak` through the existing
local world-event broadcaster. It preserves the existing destruction permissions,
block updates and `hit_wall` result. Failed or empty replacements do not request
particles. The three existing callers scan the head, neck and body after movement.

The focused fixture is `fixtures/dragon-block-break-event/cases.json`; the report
checker is `tests/check_dragon_block_break_event.py`. A connected offline
protocol-777 client records actual decoded level-event packets in a private arena.
Each trial spawns a fresh hovering dragon at (16,100,16), warms it up for two ticks,
restores its position/yaw/velocity, installs test blocks and observes one tick.
Twenty cleanup ticks separate cases. The player remains creative at (25,100,25),
and natural mob spawning is disabled. Two trials cover a body stone, a head and
body stone, griefing disabled, an immune block, a transparent block, air and NoAI.
The raw reports verify block presence/removal, phase/health, client connection,
player presence, clock delta and command errors. The checker requires event count,
zero payload, local scope, head-before-body ordering and conservative part regions.
Exact randomized coordinates are not compared between independent servers.

Vanilla passes all 14 packet cases. The campaign64 baseline passes 10/14, with
exactly four missing-event failures: body and head-plus-body destruction in both
trials. All block-removal and negative-control checks pass on both targets.
All three targets have identical controlled commands. The patched binary passes
14/14, including all four corrected event cases. Each target has 322 verified
case ticks, plus 40 setup and 20 final cleanup ticks. All scratch servers stopped,
with no ERROR, panic or exception lines in their server/client logs. All 492 pumpkin-core
library tests, workspace formatting, core all-target/all-feature Clippy and the
debug server build passed under the shared Cargo lock with one job, debug info
and incremental compilation disabled, 5GiB memory, zero swap and 200% CPU limits.
Only the existing proc-macro-error2 future-compatibility notice remains. The
source hashes before/after checks match the patch, and the tested copied binary
SHA-256 is `128d3fc6040e132f7ca8822251f6e89a9a9b0a0d42d7812b76a2a57512e4a7e0`.

The official reference is the locally downloaded 26.3 server's
`EnderDragon.checkWalls`, inspected through bytecode including the entire loop,
`removeBlock` result and final `levelEvent(2008, position, 0)`. Decompiled Java and
server files remain outside Git. Refreshed upstream master `44d881c32` retains a
block-breaking loop without this event. Fork master `65bca3f7` is already an
ancestor of this campaign branch. PR3407 covers multipart dimensions/damage,
crystal healing and phase flags; PR3661 covers part lookup; PR3835 covers fireballs;
PR4080 covers contact teams. None of their inspected patches adds this event.
The phase-classification lead was deferred because PR3407 already contains it.

Local evidence is recorded in `artifacts/christine-dragon65-upstream-overlap.json`,
`christine-dragon65-pr-search.json`, `christine-dragon65-EnderDragon.javap`,
`christine-dragon65-rust-validation.json` and `christine-dragon65-live-validation.json`.
The build, copied-binary arena and combined checker all exited zero. The build
record names parent commit `a2bb9519f39323528b7fe2acb1c6dff78ccb6368` plus the
hashed source patch; the provenance record binds the committed source to it.
The pre-push overlap refresh found unchanged heads for the inspected PRs.

Limits: packet evidence establishes that a connected headless client receives
the effect instruction; it does not show rendered particles or a whole fight.
The baseline is campaign64, not a separate upstream-master binary. Existing
multipart dimensions/positions and world-event recipient selection are unchanged;
no exact-volume or recipient-radius parity is claimed. The checker uses broad
head/body regions because the multipart foundation remains deferred upstream.
No mocked Rust getter test was added; the regression is the real world fixture.
For a rendered check, let an AI-enabled dragon break ordinary stone in an isolated
arena with mob griefing enabled and expect the dragon destruction burst. Disable
griefing and expect the stone and absence of that burst. Capture a client recording
before claiming visual proof.
