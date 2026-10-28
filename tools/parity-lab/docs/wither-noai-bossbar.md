# Wither bossbar audience with NoAI

A freshly summoned Wither with `NoAI:1b` is tracked by the campaign server but sends no bossbar. Official Java 26.3 sends an ADD with progress 1 and removes it when its observer leaves tracking range, including when `Invul:200` freezes the spawn phase.

Wither viewer membership now refreshes from `post_tick` independently of custom AI. Progress still changes in the custom AI step; NoAI retains the last progress. Moving the existing audience refresh avoids an extra scan per active tick. Corpse membership and dimension-departure handling from earlier campaign fixes remain in place.

This narrowly adapts the live `post_tick` correction in merged [upstream PR #4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092), by MegalithOfficial, commit `a1867b33ca90b483334ab2e54bb2e9113b7da94e`, to the retained campaign AI and death architecture. Fetched upstream master already fixes the defect. No upstream novelty is claimed; the wider AI rewrite is not integrated. Fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor of this branch.

`fixtures/wither-noai-bossbar/cases.json` and `tests/check_wither_noai_bossbar.py` retain focused protocol regression coverage: two trials of four active/charging cases, with and without NoAI. Each case uses a fresh boss in an isolated bedrock arena, four initial ticks, eight departure ticks and eight return ticks. It verifies actual Wither tracking, initial bossbar visibility/effective fill, range-departure entity and bossbar removal, live observer, 300 health, and the exact frozen or ticking invulnerability count. All targets receive identical gameplay commands. Return pairing is deliberately outside the assertions because the existing client does not re-pair within that short window on vanilla either.

Validation is pending the shared Cargo lock and fixed-binary comparison. Fresh official 26.3 already passes 152/152 checks; campaign93 baseline passes136/152 with exactly16 NoAI visibility/fill/removal failures across both trials. Final evidence will be recorded after the matrix and build complete. No rendered-client or whole-fight proof is claimed.

For a human play test, summon a Wither with `NoAI:1b` in an isolated arena: expect its purple bar and darkened sky, then leave entity tracking range and expect the bar to disappear. Repeat with `Invul:200` and verify the phase remains frozen. Capture a recording of both appearances and range departures before proposing upstream publication.
