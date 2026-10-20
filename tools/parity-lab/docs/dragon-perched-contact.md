# Ender Dragon perched wing push

Perched dragons now push eligible players beside their wings while keeping
wing damage suppressed. Previously Pumpkin skipped the entire contact call
in sitting phases. Vanilla 26.3 `EnderDragon.aiStep` still queries wing contacts;
`EnderDragon.knockBack` applies the outward push before its sitting damage gate.
The Rust correction runs the existing contact handler in those phases. NoAI,
creative/spectator exclusion and the recent-hurt filter retain their guards.

The focused world fixture is
`fixtures/dragon-perched-contact/cases.json`. Two trials each exercise roaring
survival/adventure contacts, breathing survival contact, and creative/NoAI
controls. The isolated arena has a stone floor at y79, a dragon at (8,80,8),
and a connected offline protocol-777 player at (12,80,8). Mob griefing, natural
spawning and health regeneration are disabled. Chunks are loaded before setup;
each fresh dragon has two warmup ticks and one observed contact tick, with
20 cleanup ticks between samples. A private client is required for the player
observations. The checker reads raw NBT and verifies health, positions, phase,
clock delta, previous-dragon removal and player presence.

| Contact result, two trials | Vanilla | Baseline | Patched |
| --- | --- | --- | --- |
| Roaring survival/adventure and breathing survival: outward impulse | 6/6 | 0/6 | 6/6 |
| Creative and NoAI: no contact impulse | 4/4 | 4/4 | 4/4 |
| Health remains 20 | 10/10 | 10/10 | 10/10 |

All three targets use identical recorded stimuli. The baseline has exactly six
missing-push failures; all other controls pass. Each target has 10 one-tick
contact observations and 270 explicitly stepped fixture ticks including setup.
All scratch servers stopped, with no ERROR or panic lines in server/client logs.
Client readiness markers, server join logs and per-case player queries establish
headless play entry; the terminated clients did not produce final client JSON.

Formatting, all 490 pumpkin-core library tests, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock, one build
job, disabled debug info/incremental, 5GiB memory, zero swap and 200% CPU limits.
Regression coverage is the world fixture/report checker; no mocked Rust unit
test was added for this call-site change. The existing proc-macro-error2
future-compatibility notice remains. The build record identifies parent
`7f3b8689510e315d1f344f98eeafdf0556f0c894` plus the hashed Rust source change.
The copied binary SHA-256 is
`fbe6f05bd5a2ead96a8e0a4aa2079c45ebe291a2ea75c047baf5547b6d26852a`.

The first final checker incorrectly required exactly zero starting horizontal
velocity. Pumpkin retains at most 0.000326 between samples. The corrected
checker bounds starting horizontal velocity and quiet-case changes below 0.001,
compared with a 0.01 impulse threshold and measured eligible impulses above 0.20.
It recomputes results from unchanged raw responses; Rust and fixture were not
changed. An earlier parser failure and a discovery run with unloaded initial
floor/residual-motion confounds are retained separately and excluded from final
proof. That discovery's hovering health mismatch is a separate follow-up lead.

Fork master is already an ancestor of the campaign branch. Refreshed upstream
PR3407/3661 cover multipart/crystal work; PR3835 covers projectiles; PR3793/3794
cover velocity plumbing; PR4080 changes contact targets/team damage but retains
the same sitting call gate. Their heads were unchanged at final review, and no
inspected PR implements this call-site correction.

Local evidence: `artifacts/christine-dragon59-rust-validation.json`,
`christine-dragon59-live-validation.json`, `christine-dragon59-source-provenance.json`
and `christine-dragon59-control-correction.json`. The final raw report is
`artifacts/christine-dragon59-live-20261020T165612.016497Z/report.json`.
Run `python3 tools/parity-lab/tests/check_dragon_perched_contact.py` with
`--vanilla`, `--baseline` and `--fixed` pointing to that report to check it.

Limits: the existing approximate player contact volume and contact-before-part
update ordering remain. This checks push presence and health, without claiming
exact Motion, nonplayer contacts, head/neck damage, client rendering or a whole
fight. A human can verify in an isolated arena by walking a survival/adventure
player beside a perched dragon's wing: expect an outward shove without wing
damage. Capture the result with a rendered client before claiming visual proof.
