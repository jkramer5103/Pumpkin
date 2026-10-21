# Dragon block removal preserves contained fluid

Ender Dragon head, neck and body block destruction must leave the removed block's
fluid state behind. The previous code always wrote air, erasing standalone water and lava.
That also lost the contained fluid of waterlogged blocks.

The official 26.3 `EnderDragon.checkWalls` delegates to `Level.removeBlock(pos,
false)`, which writes `getFluidState(pos).createLegacyBlock()` using flag 3.
An unchanged standalone fluid is not a successful removal and emits no dragon
block destruction event. Pumpkin's existing fluid-state lookup supplies the
replacement block state, including source water for waterlogged blocks and the
level of standalone fluid. Only dragon-specific source is changed; existing
protection checks and block notification flags remain in use.

## Regression

`fixtures/dragon-block-fluid/cases.json` defines two trials of nine cases.
`tests/check_dragon_block_fluid.py` checks raw isolated-world reports from
vanilla, the pre-fix campaign binary and the patched server. It checks block
states after exactly one controlled AI tick and decoded protocol 777 dragon
block destruction events. Standalone source water and lava must remain without an event.
Dry slab/stone destruction, disabled griefing, NoAI, immune blocks, transparent
blocks and air provide controls. Each target executes identical gameplay commands with
an actual headless logged-in player and verifies loaded arena, health, phase,
position, tick advancement, client liveness and final cleanup.

Before-fix comparison: vanilla 18/18 cases, baseline 14/18, with exactly the four
water/lava cases failing (deleted fluid and spurious event). All controls pass.
Each target advances 414 verified case ticks plus 40 setup and 20 cleanup ticks.
Workspace formatting, all 492 `pumpkin-core` library tests, core all-target and
all-feature Clippy, and the debug server build passed under the shared Cargo
lock, one build job, disabled debug info/incremental, and required resource limits.
The existing `proc-macro-error2` future-compatibility notice remains. An initial
compile was interrupted after review found the obsolete import; the corrected
source passed all checks. Patched comparison: 18/18 cases, matching vanilla. All setup, phase/health,
position, client, tick, protection and cleanup controls pass. Controlled-command
hashes are identical across all three targets. Source, copied binary, fixture
and checker hashes were verified; scratch servers stopped and server/client logs
have no errors, panics or exceptions. The world fixture/checker supplies focused
regression coverage; no synthetic Rust getter test was added.

Initial wet-block/flowing-fluid commands were rejected
by Pumpkin's property parser; these invalid setup reports are excluded. The final
fixture uses property-free placement and block checks. Waterlogged and flowing
fluid behavior follows the source path but is not live-validated here. No
rendered-client or whole-fight proof is claimed.

## Scope and overlap

The upstream tracker and Mob AI issue 3468 are leads. The multipart hitbox,
entity lookup/despawn, crystal/healing, phase sitting flag and fireball foundation
work remains deferred to PRs 3407, 3661 and 3835. Their refreshed patches do not
change this fluid replacement path. Upstream master 44d881c32 retains unconditional
air replacement. The live baseline is campaign 65 (7877e4b3b), not a separately
built upstream master. Fork master 65bca3f7f is already an ancestor of the campaign
branch, and existing campaign source fixes are preserved.

## Real-client follow-up

In a scratch arena, allow a hovering dragon's body to intersect water and lava.
Expect the fluids to remain without a destruction burst. Repeat with dry slabs:
they disappear with a destruction event. Disable mob griefing and confirm blocks
remain intact. As additional coverage, intersect a waterlogged oak slab and check
that the slab disappears while source water remains; this last case was not
validated by the headless fixture.
Record the block changes and particles from a real client before any human
upstream submission. This campaign does not open upstream PRs.
