# Ender Dragon contact push

The dragon's collision handler used ordinary combat knockback. That normalizes
and subtracts the horizontal vector, halves existing horizontal velocity, and
only raises grounded targets. Vanilla 26.3 `EnderDragon.knockBack` instead adds an
outward vector scaled by inverse squared horizontal distance, with a minimum
squared distance of 0.1 and a fixed 0.2F upward impulse.

The correction uses `Entity::add_velocity`, which also sends the velocity update,
and calculates the origin from the current body-part position. The body-position
helper is shared with part placement so collision processing cannot use a stale
body position. Two Rust tests cover opposite directions, distance scaling,
diagonal contact, the distance clamp and exact center contact.

Validation used isolated vanilla 26.3, current-source baseline 9fff3648, and
patched source 36bf02d8. Every sample waited 210 verified cleanup ticks and
asserted that no old dragon remained before summoning one. A protocol 777
headless client held chunks loaded. It used creative mode during cleanup and
survival with Resistance V during contact. Six samples per target covered
horizontal offsets +4, -4 and +6 in two repeats.

| Target | Outward increments | No measurable increment | Nearer stronger, +4 vs +6 |
| --- | ---: | ---: | --- |
| Vanilla | 6 | 0 | Both repeats |
| Baseline | 0 (five inward) | 1 | Neither repeat |
| Patched | 5 | 1 | Both repeats |

All five measurable patched impulses matched the corrected horizontal formula
within 1e-6 and added exactly the widened 0.2F vertical impulse. At offset +4,
the X increment was about 0.984615; at +6 it was about 0.662069. One patched
sample produced no measurable impulse; its phase/tick eligibility was not
established. This is a coverage gap, not an all-samples parity pass.

Formatting, all 449 pumpkin-core library tests, all-targets/all-features core
clippy, and the full Pumpkin build passed under the shared build lock and
resource caps. All 18 dragon-absence preconditions passed; no environment errors
were detected, all three scratch servers stopped, and their logs contained no
ERROR/panic lines. Earlier allowlist, teleport, floating-client and overlapping
death-sequence attempts remain preserved as incomplete or limited evidence.

Deployment evidence: `artifacts/christine-dragon10-final-validation.json` and
`artifacts/christine-dragon10-final-rust-validation.json`. The full command and
motion report is `artifacts/christine-dragon10-live-20261016T120814.295048Z/report.json`.
Source correction: ae58abe5fd4afeaa382c3589494fd0ddfe0432b8; literal-style followup
and validated build: 36bf02d8f140e81717d7a11bae11a6f4a5ce95bd. Patched binary SHA-256:
`9101941546b07dae02399f8b1468cc1742acad4799704a94c60d9b4ac7add69f`.

This is a correction of the contact impulse. Main-body collision selection,
creative/spectator and hurt-time gates, contact damage timing, and damage to
non-player entities require separate work. The probe is server-observable
headless gameplay evidence; it does not establish client rendering, movement
prediction or whole-fight parity. Vanilla player motion also has server-side
physics that Pumpkin's client-authoritative player movement does not share;
raw Motion vectors are not claimed to be identical.

Upstream was checked at 5b53f064af8708ba33fcaa533b81ca29a53a3310. Open PRs 3407
and 3661 cover multipart registration, phase classification and crystal healing.
Those changes were excluded. Closed, unmerged PR 2383 proposes once-per-contact
gating; this correction preserves continuous contact processing and follows the
vanilla push calculation instead.
