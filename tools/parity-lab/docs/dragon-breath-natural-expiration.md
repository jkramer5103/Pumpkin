# Dragon breath natural expiration

Sitting dragon breath clouds stayed alive and kept damaging later victims after
vanilla's natural expiry. Pumpkin now gives each emitted cloud a 200-tick
duration and counts its 20-tick wait before that duration. It survives through
cloud age 219 and expires at age 220 even when its dragon's AI is paused.

## Vanilla call chain and correction

Vanilla 26.3 `DragonSittingFlamingPhase.doServerTick` sets the cloud duration to
200. `AreaEffectCloud` defaults to waitTime 20 and expires before applying
effects when its tick count minus waitTime reaches duration. Duration -1
disables age expiry. Pumpkin configured 600 and removed at age greater than
duration, ignoring the wait period. Both settings need correction for this
flame's natural lifetime to match vanilla.

The shared expiry rule also affects summoned/default clouds, lingering potion
clouds and the current strafing cloud. Finite clouds count their configured wait
before their duration, with the exact end excluded. Radius changes and contacts
can still discard a cloud earlier. The Rust boundary tests cover waiting,
zero wait, zero duration and unlimited duration. The latter is an age-expiry
check only; constructors and other removal paths remain separate.

## Focused regression

`lab/examples/dragon-breath-natural-expiration.json` runs two isolated trials
with a protocol 777 headless client. Each uses the naturally emitted flame's
actual position for a marker and sheep. The dragon receives NoAI after emission
and moves away. A sheep introduced at cloud age 205 must lose three health by
210. The original cloud must survive at 219 and disappear at 220 while the
dragon remains paused in phase 5. A fresh sheep must stay healthy through 225.
Tick barriers verify every requested interval.

Vanilla and patched Pumpkin passed 29/29 checks; baseline c27ef9f passed 25/29,
failing both natural removal checks and both post-expiry sheep-health checks.
Fixture hashes and gameplay stimulus commands match across all three runs. All
three scratch processes stopped. Both Pumpkin servers completed their saves.
Vanilla's final save marker was not observed within the existing harness grace.
Server logs contain no errors or panics; client logs contain no errors. Existing
Java native-access warnings remain.

Rust validation passed under the shared Cargo lock, one build worker, disabled
debug information and incremental compilation, and the prescribed systemd
memory and CPU limits:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 464 passed, including three new tests
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

The first run stopped on Clippy's missing-const-fn rule after passing tests; the
corrected run passed every check. Source and copied binary hashes agree. The
existing proc-macro-error2 future-compatibility warning remains. The owned prior
baseline binary was losslessly archived with a verified decompressed hash.

## Scope and limitations

Fork master 65bca3f is already an ancestor. Fetched upstream master 998c3f8 has no
newer changes in the affected paths. Open multipart PRs 3407/3661 do not change
this duration or cloud expiry; cloud PR 3663 concerns creeper emission.

The fixture restores phase 5 directly and uses actual cloud positions. It gives
server-state evidence, with no rendered-client capture or complete fight proof.
Cloud placement, particles, ownership, effect eligibility and the full sitting
cycle remain separate. Lingering-potion and strafing gameplay were not exercised
by this dragon fixture. The completed active phase timer and phase-exit cleanup
are separate from this cloud's natural expiration.
