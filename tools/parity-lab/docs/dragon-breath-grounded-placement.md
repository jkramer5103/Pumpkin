# Dragon breath grounded placement

Sitting dragon breath was emitted two blocks behind the body and half a block
above it, missing ground victims in front of the head and damaging entities at
the wrong position. The phase now places the cloud 2.5 blocks ahead of its head
and searches down to the first non-air block, following vanilla 26.3
`DragonSittingFlamingPhase.doServerTick`.

The head position is read before this tick's part update, as in vanilla's
`EnderDragon.aiStep`. The search starts at the one-block-tall head's vertical
midpoint. Block coordinates use floor, including negative coordinates. If the
search passes below zero, vanilla restores the initial head height; the result
is floor(height) + 1. This zero cutoff is intentional and independent of the
world's minimum build height. The search stops at any non-air block, including
blocks without a solid collision shape.

The correction only changes sitting-breath placement. Cloud radius, damage,
lifetime, phase transitions, ownership, particles, and multipart dimensions and
registration are outside this patch.

## Focused regression

`lab/examples/dragon-breath-grounded-placement.json` runs two trials each of:

- A level arena: dragon at (0.5,100,0.5), cloud at (0.5,80,-8.5).
- A dragon rotated 90 degrees and a raised platform: cloud at (9.5,90,0.5).
- An empty column down through zero: cloud at (0.5,100,-8.5).

Each dragon starts in the roar phase and naturally enters breath after 40 ticks,
then emits at tick 50. This allows its head history to settle before placement.
After emission, NoAI pauses the dragon and it moves away. A sheep
at the expected cloud position must lose three health; a sheep at the old
body-relative position must stay healthy. Exact tick barriers, position checks
and a connected protocol-777 headless client are recorded for each target.

Vanilla and patched Pumpkin passed 43/43 checks; baseline ff88cf4 passed 19/43,
failing every cloud-position and front/old-center sheep-health assertion.
Commands and fixture hashes matched across the three targets, with 450 verified
gameplay ticks per target. All three scratch processes stopped. Both Pumpkin
servers completed their saves; vanilla's final save marker was not observed
within the harness grace. Server and client logs have no errors or panics;
existing Java native-access and offline-mode warnings remain.

The original newborn fixture passed 43/43 on vanilla, 19/43 on baseline and
25/43 on the first patch. Grounding corrected, but a separate flight-history
startup defect distorted the head position. The final fixture uses a natural
roar before breath on all targets. The original reports remain in task32
artifacts and are not counted as successful patched validation.

Three Rust regression tests cover head-relative placement and terrain descent,
empty-column fallback without sampling below zero, and an occupied starting
block with negative coordinates and a fractional head height.

Rust validation passed under the shared Cargo lock and prescribed resource limits:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 467 passed
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

The existing proc-macro-error2 future-compatibility warning remains.

## Provenance and limitations

Fetched fork master 65bca3f is already an ancestor of the lane. Fetched upstream
master 998c3f8 still uses the body/yaw offset. Open PRs 3407 and 3661 concern
multipart damage and entity lookup, and do not implement sitting-breath
placement. PR3835 changes projectiles; PR3663 concerns creeper clouds. Search
results and vanilla source hashes are retained in task32 artifacts outside Git.

The comparison restores the roar phase in isolated overworld arenas with
loaded chunks and lets the dragon enter breath naturally. It gives server-state evidence, with no rendered-client capture
or full boss fight proof. Terrain reads use Pumpkin's existing loaded-block API;
unloaded chunks and natural End portal landings were not exercised. Cloud owner,
particle appearance, the missing scanning phase and the full sitting cycle
remain independent leads. Newly summoned dragons forced directly into breath
retain the separate flight-history startup discrepancy; this patch uses their
actual head position, which is transiently incorrect before history settles.

For human play testing, join a scratch End arena, watch a perched dragon breathe
across level and raised ground, and check that the flame appears ahead of its
head with victims on that ground taking damage. Record both orientations and
the effect on victims. Capture: <attach screenshot or recording here>.
