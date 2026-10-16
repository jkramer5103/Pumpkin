# Ender Dragon contact game modes

Before this patch dragon contact pushed creative and spectator players. Vanilla 26.3
`EnderDragon.aiStep` filters wing, head and neck queries with
`EntitySelector.NO_CREATIVE_OR_SPECTATOR`; that predicate excludes either player
mode, while survival and adventure remain eligible. Contact damage must use the
same filter. This task is limited to that eligibility decision.

Fresh fork master and upstream master were fetched. Fork master is already an
ancestor of the campaign branch. Open PRs 3407 and 3661 cover multipart lookup,
part dimensions, crystals and fight state; neither changes this eligibility
filter. PR 3793 changes velocity plumbing without adding a mode filter.

The focused Rust regression failed with the original unconditional eligibility
(extracted without changing behavior): one failed test, Cargo exit 101. The
source correction filters players before contact push and damage, retaining
survival and adventure eligibility.

Isolated baseline observations used an offline protocol-777 headless player,
one dragon per sample and a bounded stone arena with mob griefing disabled.
Across two repetitions, creative contact produced a horizontal/upward impulse
in both samples and spectator contact did so in one of two. The other spectator
sample had no measurable impulse; its tick eligibility was not established.
Survival and adventure controls produced impulses in all four samples.
Vanilla produced no horizontal impulse in all four excluded-mode samples and
pushed in all four survival/adventure samples. Its eight rows and clean shutdown
were saved before interruption of the following baseline target; that combined
run is incomplete and is not counted as a completed whole run.

Rust validation passed: formatting, 450 pumpkin-core library tests, core clippy
with all targets/features, and the full Pumpkin binary build. All Cargo
operations ran under the shared build lock, one build job, disabled debug info
and incremental compilation, and the documented memory/CPU caps. The existing
proc-macro-error2 future-compatibility warning remains.

The built source diff exactly matched source commit
`944799a` before commit; the immutable binary SHA-256 is
`0fa66eae1ac8b213add4b885916c48aa1ba05d33e07c72675a3ecb6d26728ee9`.
The original build record identifies the parent commit plus that source diff.
The patched run produced no horizontal impulse in all four excluded-mode
samples. Both survival samples and one adventure sample produced the expected
outward/upward impulse. The first adventure sample had no measurable impulse;
it is a coverage gap, not a passing control. This patch does not establish why
some otherwise eligible contacts produce no impulse.

All three targets used identical fixture commands apart from variable clock
poll counts; recorded clock deltas verify each requested step, including the
single contact tick. Exact dragon/player starting positions were checked for
all 24 samples. The completed vanilla target, completed baseline replay and
patched target stopped cleanly, with no ERROR/panic lines in their console logs.
Known development/fresh-world warnings and delimiter scoreboard errors are
retained in the raw logs.

Evidence: local `artifacts/christine-dragon11-rust-validation.json`,
`christine-dragon11-live-validation.json` and `christine-dragon11-final-validation.json`.
The stricter all-controls summary failed on that adventure sample; its output
is retained at `christine-dragon11-initial-summary.log`. Final evidence records
four excluded-mode passes, three measured positive controls and one control gap.
No visual client or full fight claim is made.

Remaining candidates: reproduce the dragon hurt cooldown gate and the two-tick
contact-damage guard. Check the open multipart PRs before changing collision
volumes. Contact while perched, other living entities and team damage eligibility
also remain separate work.
