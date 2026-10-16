# Dragon death experience and mob_drops

Pumpkin's dragon death sequence spawns periodic XP after tick 150 and a final
payout at tick 200 even when `mob_drops` is false. Vanilla 26.3
`EnderDragon.tickDeath` gates both awards on `GameRules.MOB_DROPS`, while still
completing death, removing the dragon and notifying its fight.

Scope: gate both awards in `phase/dying.rs`; keep fight completion and removal
outside the gamerule condition. Focused regression fixture:
`lab/examples/dragon-death-experience-rule.json` checks disabled and enabled
rules, no premature payout, periodic XP at tick 155 and final payout/removal
at tick 200. A fixed UUID keeps the dying entity addressable after `@e` excludes
it. Player-attributed damage and a subsequent zero-health load isolate the
animation from flight to the podium; they do not validate that flight.

Upstream review: fork master `65bca3f` is already an ancestor of the campaign
branch. Upstream `b57d821` has no change to this file. Open PRs 3407 and 3661
cover other dragon behavior and do not gate these XP awards. Read-only issue/PR
search evidence is retained outside Git in the live lab artifacts.

Validation: all 456 `pumpkin-core` library tests, workspace `cargo fmt --check`,
`pumpkin-core` all-targets/all-features clippy and a full debug server build
passed under the shared build lock with one Cargo job, debug info/incremental
disabled and the required resource caps. The existing `proc-macro-error2`
future-compatibility warning remains.

Two isolated repetitions with each rule value passed 40/40 focused checks on
vanilla and patched Pumpkin. Baseline Pumpkin passed 36/40, failing only the
four disabled-rule XP assertions. Both versions retain the corpse at ticks
154/199 and remove it at tick 200. The enabled-rule control produces orbs at
155 and 200, while the patched disabled-rule case produces none. All core
command stimuli match across targets after removing timing-query polling.
The committed regression fixture passed 14/14 checks on vanilla and patched
Pumpkin; baseline passed 12/14, failing only the two disabled-rule XP assertions.
Combined core/fixture evidence: vanilla and patched 54/54, baseline 48/54.
Fixture hashes and command stimuli match across all three targets; all six
scratch servers stopped, and their logs contain no ERROR/panic lines.

Build base was `20a42d7` plus the recorded seven-line Rust diff; validated death
source SHA-256 is
`6dac295e760d25104dea703a0828211e7dd90400077a8bacbc697916702e25e5`.
The archived binary SHA-256 is
`6aea58d22e64edf2f7be0f3e931872dc251a97bf88abf2369fe9c55b916c66d0`.
Live lab artifacts retain Rust results, source/binary provenance and raw reports
under `christine-dragon16-*`. The first scratch report used invalid `@e` corpse
presence checks and is excluded; the corrected reference uses the fixed UUID.

Limits: headless protocol 777 server state only. No real-client visual or full
fight proof. Zero-health loading bypasses death flight; natural End fight and
portal creation, save/reload and first-kill XP amounts are not exercised. The
last tick checks combined periodic/final orb presence, not individual amounts.
The fight-completion call remains outside the new gate by source review.

Next leads: phase persistence cannot safely be added as a field alone: current
Rust phase IDs differ from vanilla's IDs and there is no sitting-scanning phase.
Investigate actual resumed AI with a vanilla/Pumpkin reload comparison before
changing it. Dragon protected-block slowdown/in_wall remains another lead.
Do not repeat completed initial-hover, NoAI or contact-gate tasks.
