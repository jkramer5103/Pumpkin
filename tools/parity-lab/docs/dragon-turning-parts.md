# Dragon turning head and neck orientation

A turning dragon now applies its head and neck lag in radians after converting
the body yaw. Previously the lag was incorrectly converted from degrees as well,
reducing it by roughly a factor of 57 and shifting the block-breaking footprint
to the wrong side during a turn. The correction changes only the angle used to
position those two parts.

The reference is official vanilla 26.3 `EnderDragon.aiStep`, after phase steering
and before `checkWalls`. Vanilla computes `yaw * (PI / 180) - yRotA * 0.01`.
The scratch arena seeds a hover target, teleports the dragon 30 blocks away,
resets motion, and advances one tick. At yaw zero facing away from that target,
vanilla and Pumpkin both turn to -3.5 degrees. Vanilla removes stone at
(2,100,-36) and preserves (-2,100,-36); previous Pumpkin does the reverse.
Two exploratory trials reproduce all eight expected block-state differences;
straight, distant and NoAI controls pass on both servers.

Upstream master and the heads of open [PR3407](https://github.com/Pumpkin-MC/Pumpkin/pull/3407) and
[PR3661](https://github.com/Pumpkin-MC/Pumpkin/pull/3661) retain the erroneous
expression. Fresh searches for open dragon, hitbox and yaw work found no
equivalent correction. The multipart registration and incoming-damage portions
of those PRs remain outside this change. Fork master was fetched and is already
an ancestor of this campaign branch.

## Validation

All 481 core Rust library tests, workspace formatting, core Clippy (all targets
and features), and the debug server build passed under the shared Cargo flock,
one build job, disabled debug info/incremental compilation, and a 5-GiB/no-swap/
2-CPU systemd scope. The existing proc-macro-error2 future-compatibility warning
remains. No new isolated math test was added: the retained regression exercises
actual world block destruction through the part positions.

The final reference fixture passes 157/157 checks on vanilla and 141/157 on the
previous Pumpkin, with exactly 16 expected block-state failures. Each target
advances 49 controlled ticks over two trials. Position and motion are compared
within 0.0001; yaw orientation is compared modulo 360 degrees. Four samples
store -183.5 degrees on vanilla versus the equivalent 176.5 degrees on Pumpkin;
raw values remain in the evidence. Repeated vanilla observations match exactly.

The patched binary passes all 157/157 checks on the identical fixture, including
the 16 previously failing block observations. Fixture, stimulus, Rust source
and copied-binary hashes were verified. All scratch servers stopped; both
Pumpkin saves completed. Vanilla's final-save completion marker was not observed
within the shutdown grace, so only process termination is confirmed there.
No server ERROR or panic lines were logged. Existing development/debug-build,
vanilla offline-mode and Java native-access/deprecation warnings remain.

The connected headless client was present on all three targets. These checks
use server block state, with no screenshots or visual-animation evidence.

Focused regression: `lab/examples/dragon-turning-parts.json`. Two trials cover
both turn directions, a rotated heading, neck-only height, corrected and former
footprints, straight flight, a distant block and NoAI. Position, motion and yaw
are recorded to distinguish geometry from changes in flight movement.

This is headless protocol-client and server-state evidence. No rendered-client,
complete boss fight, natural-flight sequence, incoming part damage or visual
animation proof is claimed. Existing contact-hitbox routing remains separate.

Local evidence in the deployment workspace:
`artifacts/christine-dragon45-rust-validation.json`,
`artifacts/christine-dragon45-live-validation.json`, and
`artifacts/christine-dragon45-source-provenance.json`.
The local vanilla `EnderDragon.java` SHA-256 is
`fa6e7606d14171d304288e23f97decacadfff132c2f16ae8547b66c3ecaa877c`.
