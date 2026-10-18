# Sitting dragon breath warmup

Pumpkin emitted the sitting breath cloud on the first active breathing tick.
Reentering breathing retained an incomplete old timer and could suppress the next
cloud. Vanilla 26.3 `DragonSittingFlamingPhase.begin` resets the clock and its
server tick creates the cloud at tick 10. The Rust phase now does both.

## Reproduction and coverage

`lab/examples/dragon-breath-warmup.json` observes actual area effect clouds in an
isolated arena with a protocol 777 headless client. Two fresh phase entries check
absence at ticks 1 and 9, exactly one cloud at 10 and 11, and no second emission
after removing it. Further cases check incomplete phase reentry, NoAI pauses,
resuming AI, and same-phase NBT merges preserving elapsed time. Explicit tick
barriers verify every requested time delta.

Vanilla and patched Pumpkin each passed 46/46 checks. Baseline Pumpkin e513746
passed 38/46, failing eight cloud checks. All three runs used identical fixture
hashes and gameplay commands. Source and binary hashes, exact tick barriers,
client presence and error-free server/client logs were verified. All three
scratch processes stopped; both Pumpkin shutdown completion markers were seen.
Vanilla logged saving but did not record its completion marker within the
existing harness grace period.

Rust validation passed under the shared build lock, one Cargo worker, disabled
debug information/incremental compilation, and the prescribed systemd memory/CPU
limits:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 460 passed
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

The existing proc-macro-error2 future-compatibility and Java native/Unsafe
warnings remain. One own historical binary was losslessly archived with a
verified decompressed hash to preserve build disk headroom.

## Scope and provenance

Fork master 65bca3f was already integrated into this branch; upstream master
998c3f8 retains the incorrect warmup. Open dragon PR3407 (a0cb2be), PR3661
(e7e5449) and projectile PR3835 were inspected read-only; none corrects this
breathing timer. Multipart collision/damage and healing changes overlap existing
upstream work and were not duplicated. The changed source is confined to
`ender_dragon/phase/sit_breathing.rs`; the Wither lane owns a separate boss file.

These are server-state cloud observations, not rendered-client or full-fight
proof. Tests restore phase 5 directly. Natural roar-to-breath dispatch still has
an independent scheduling discrepancy: vanilla ticks a newly selected phase in
the same AI step, whereas Pumpkin defers it to the next step. Cloud position,
radius, ownership, effects, lifetime, cleanup on phase exit, flame-cycle count,
scanning and natural End fight behavior remain separate unvalidated work.
