# Dragon protected-wall slowdown

A flying dragon now reduces displacement by 20% on the tick after its head,
neck, or body meets a block it cannot destroy. Leaving the wall clears that
slowdown after the next scan. Air and dragon-transparent blocks do not count;
destroyable blocks are removed instead. Wings, tails and the main entity box
are excluded from the scan.

Previously `in_wall` was initialized false and never updated. Block breaking
ran before movement against the main 16-by-8 box and skipped several phases.
The correction runs vanilla's `checkWalls` equivalent after updating the parts,
checks all three volumes without short-circuiting, and records the result for
the existing flight slowdown. The scan includes the floored maximum block
faces, as vanilla does, rather than the epsilon-adjusted general collision bound.
The existing NoAI and death-animation early returns still bypass this work.

The dimensions dependency reuses the per-part initialization from
[zinedinp's upstream PR3407](https://github.com/Pumpkin-MC/Pumpkin/pull/3407),
source head `a0cb2beaf3ba33d93d706e6d229838e7760919b1`, adapted to the current
fork. Only dimensions are included. Part registration, incoming damage,
despawning and crystal healing remain with that upstream work. Fresh open-PR
searches and PR3407/3661 file review found no equivalent protected-wall scan.
Fork master was fetched and already an ancestor of the campaign branch.

The reference is the local official vanilla 26.3 `EnderDragon.aiStep`,
`checkWalls`, and constructor. Local decompiled source SHA-256:
`fa6e7606d14171d304288e23f97decacadfff132c2f16ae8547b66c3ecaa877c`.
The observed body-bedrock case moves from Z 30 to 29.9400000013 on tick one.
On tick two vanilla reaches 29.8464000020, while the previous Pumpkin reaches
29.8230000040, the same as unobstructed flight. Removing the wall retains one
last slowed displacement and then restores normal movement.

## Validation

All 481 core Rust library tests, workspace formatting, core Clippy (all targets
and features), and debug server build passed. The existing proc-macro-error2
future-compatibility warning remains. Initial arena preparation failures were
corrected with five setup ticks and shared block-read assertions. The failed
preparation runs remain in local evidence; no Rust source change or assertion
suppression was needed. Terminal `execute if loaded` was unsuitable for this
fixture because it is unsupported on both Pumpkin binaries.

Final identical-fixture comparison: vanilla and patched Pumpkin each passed
327/327 checks; previous Pumpkin passed 267/327, with exactly the 60 expected
protected-wall position failures. All other controls passed. Each target ran
105 controlled ticks across two trials. Raw vectors match vanilla within
0.0001; repeated vanilla trials match exactly. Fixture, stimulus, Rust source
and copied-binary hashes were checked. No new isolated Rust unit test was
added: the world-dependent regression is retained as the arena scenario.

All three scratch servers stopped, both Pumpkin saves completed, and no server
ERROR or panic lines were logged. Vanilla final-save completion was not
confirmed within the shutdown grace period; process termination was verified.
The connected headless client was present in all three targets.

Local evidence: `artifacts/christine-dragon44-rust-validation.json`,
`artifacts/christine-dragon44-live-validation.json`, and
`artifacts/christine-dragon44-source-provenance.json` in the deployment workspace.

Focused regression fixture: `lab/examples/dragon-wall-slowdown.json`.
Two trials cover head, neck, body, the body's upper block boundary, bedrock,
stone with mob griefing enabled/disabled, air, and wing/tail/distant controls.
Four position observations and two velocity observations per case capture
initial detection, next-tick slowdown and recovery after clearing the block.
The fixture uses the existing isolated arena and connected headless protocol
client. No rendered-client or complete dragon-fight validation is claimed.

The source checks run under the shared Cargo flock, one build job, disabled
debug info/incremental compilation, and a 5-GiB/2-CPU systemd scope:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

Limitations: the axis-aligned hovering fixture does not prove natural flight,
turning/tilted part placement, sitting or dying-flight wall behavior, visual flap
or block-break effects. Block-break particles/events are a separate existing
gap; this patch preserves the existing set-block destruction path. Multipart
registration and contact hitbox selection remain incomplete. This is bounded
regression evidence, not whole-boss or campaign parity.
