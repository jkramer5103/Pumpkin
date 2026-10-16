# Ender Dragon initial hover

Vanilla 26.3's EnderDragonPhaseManager starts in HOVERING. DragonHoverPhase
captures the dragon position on its first active tick and keeps that target
until another phase is selected. Its begin method clears the target and its
fly speed is 1.0. EnderDragonFight.createNewDragon explicitly selects
HOLDING_PATTERN for a fight-created dragon.

Pumpkin instead creates every dragon in Circling. Its unused hover phase
chooses an arena-origin target and has a random transition to TakingOff.
The bounded patch starts standalone dragons in Hovering, captures their initial
position and removes that random transition. Fight-created dragons explicitly
select Circling, preserving their existing fight startup.

Reference classes were decompiled locally from the official 26.3 server jar.
Upstream master b57d821 and fork master 65bca3f were inspected; fork master was
already integrated. The relevant dragon files are unchanged between the baseline
upstream 5b53f06 and b57d821. Open PRs 3407/3661 concern parts, incoming damage, crystals,
bossbars and despawn. They do not change initial phase or HoveringPhase target
selection. PR3407 does overlap sitting classification; this patch leaves that
separate behavior untouched. No upstream PR or issue was opened.

Rust validation passed: `cargo fmt --all -- --check`, 456 tests from
`cargo test --locked -p pumpkin-core --lib`,
`cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
`cargo build --locked -p pumpkin`. All Cargo operations used the shared build
lock, one build job, disabled debug info/incremental compilation, and the
5 GiB/zero-swap/200% CPU scope. A prior interrupted build had no test result and
is excluded from these results.

The permanent dragon-initial-hover.json arena fixture checks
that the dragon stays within one block of its spawn after 40 active ticks.
The local comparison additionally records exact positions and game-time deltas,
runs twice, and includes NoAI controls and eventual cleanup. This is a coarse
movement criterion, not proof of exact flight dynamics or a complete boss fight.

Separate limitations: network phase IDs/metadata and DragonPhase NBT persistence,
hover sitting classification, multipart contacts and existing flight integration
remain independent defects or leads. No client visual proof is claimed.

The natural fight creation path explicitly selects Circling, as in vanilla. That
path was reviewed and compiled; the isolated replay does not create a natural
End fight or exercise re-entry into Hovering after another phase.

Final isolated protocol-777 replay: vanilla and patched Pumpkin each pass 32/32
focused checks; baseline passes 29/32. After 40 active ticks, the two vanilla
trials are 0.01865 blocks from spawn, baseline 13.69995/13.74043, and patched
Pumpkin 0.03421/0.03421. Thus the coarse hover criterion passes; exact movement
still differs. Both NoAI trials on every target remain at the spawn position.
The fixture independently reproduces the baseline failure and passes on vanilla
and the patched binary. All twelve core samples have matching command sequences,
exact starting coordinates and 40-tick deltas, client-presence and cleanup checks.
All six scratch servers stopped; console logs contain no ERROR or panic lines.

Local evidence (not published with worlds, logs or binaries):

- `artifacts/christine-dragon15-rust-validation.json`: successful commands and
  tested source/binary hashes.
- `artifacts/christine-dragon15-live-validation.json`: assertions over core and
  committed-fixture reports, including the expected baseline failures.
- `artifacts/christine-dragon15-source-provenance.json`: source diff, hashes and
  stopped-server logs. The first interrupted build remains separately recorded.

Source commit: `b630fbbe7cf2d632c0f17931110a543cc1aca0bd`. Tested binary SHA-256: `6ca71c7a4b456d99aad45a563554e6892cd5810668e2d8304ef2c04d8973cd65`.
