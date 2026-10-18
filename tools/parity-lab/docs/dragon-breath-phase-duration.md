# Sitting dragon breath phase duration

Pumpkin ended the sitting breath phase on active tick 101, removing its emitted
cloud and leaving later victims unharmed. Vanilla 26.3 keeps the phase through
tick 199 and ends it on tick 200. The Rust phase now uses that boundary.

## Focused reproduction

`lab/examples/dragon-breath-phase-duration.json` runs two isolated trials with a
protocol 777 headless client. It tags the original emitted cloud, checks phase
and cloud presence at ticks 100, 101 and 199, and checks removal on tick 200.
A sheep introduced at tick 120 at the actual cloud center must lose three health
by tick 125. The second trial pauses AI for 30 world ticks before resuming the
same active-phase clock. Explicit barriers verify each requested tick delta.

Vanilla and patched Pumpkin each passed 40/40 checks. Baseline Pumpkin ed54a8b
passed 30/40, failing ten phase, original-cloud and late-victim checks.
Gameplay commands and fixture
hashes matched; settling reads of game time may differ in number. All three
scratch processes stopped. Both Pumpkin servers completed their saves;
vanilla's final save completion marker was not observed within the existing
harness grace period.

Rust validation passed under the shared build lock, one Cargo worker, disabled
debug information and incremental compilation, and the prescribed systemd
memory and CPU limits:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 461 passed
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

Source and binary hashes matched the successful build and live run. Server and
client logs showed no errors or panics. The existing proc-macro-error2 future
compatibility and Java native-access warnings remain. Two owned historical
binaries were archived losslessly with verified decompressed hashes to preserve
build disk headroom.

## Scope and limitations

The source correction changes only the sitting breath duration boundary.
Existing warmup, timer reset, emission and phase-exit cleanup stay in place.
Fork master 65bca3f is already integrated. Upstream master 998c3f8 still uses the
incorrect boundary; its newer unrelated commits do not change dragon code.
Open multipart/contact PRs 3407 and 3661 do not fix this duration.

This fixture restores phase 5 directly and measures server state relative to
each cloud's actual position. It provides no rendered-client or whole-fight
proof. Cloud placement and natural expiration remain separate. Pumpkin still
selects the attacking phase after breathing instead of vanilla's scanning
phase, and lacks the four-flame counter. The regression checks leaving phase 5
at tick 200 without claiming parity for the successor or complete sitting cycle.
