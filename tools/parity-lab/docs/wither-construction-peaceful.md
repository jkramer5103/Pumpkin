# Wither construction on Peaceful

Vanilla 26.3 preserves the soul-block T and all three skulls when the player
places the final skull on Peaceful. Pumpkin's construction callback lacked the
difficulty gate, consumed the structure and created a boss that its Peaceful
mob tick then removed.

The correction returns from the Wither skull placement callback after creating
the skull block entity and before pattern detection or block removal when the
world difficulty is Peaceful. Ordinary skull placement still completes. The
existing entity spawn event and non-Peaceful construction path remain in place.

Vanilla reference: `WitherSkullBlock.checkSpawn` checks the level difficulty
before matching the full pattern, clearing blocks or creating the Wither.
The reference was decompiled locally from the official 26.3 server. The
tracker and Mob AI issue #3468 were reviewed as leads; the spawn-window AI goal
is already fixed on this branch. Current upstream master still lacks the
construction gate. Fork master is an ancestor of this branch, so no merge was
needed. Open Wither, skull and Peaceful PR searches, including the complete
file lists of the large AI proposals #4092 and #4107, showed no overlapping
construction fix.

The focused `wither-construction-peaceful.json` world regression uses the
existing protocol777 placement client. At each `PARITY_BUILD_PLACE` marker,
the driver sends one main-hand `UseItemOn` packet against the indicated
soul block; command-only skull placement does not exercise vanilla's player
placement callback. Both horizontal axes alternate Peaceful and Easy in two
trials, checking all seven pattern blocks, boss presence, spawn packets,
placement transmission and player readiness. The base is checked again after
20 more controlled ticks to catch consumption followed by immediate despawn.

Vanilla and the patched binary passed 128/128 focused checks across both trials.
The pre-fix binary passed 92/128, with exactly 36 expected failures for consumed
blocks and transient boss spawn packets on Peaceful. Easy controls passed on
all targets. Each target advanced 401 controlled ticks including cleanup.
Fixture, gameplay-command, source and copied-binary hashes match. All three
scratch processes stopped and cleanup passed; both Pumpkin saves completed.
Server/client logs contain no ERROR, panic or uncaught-thread-exception lines.
Vanilla final-save completion was not verified within the shutdown grace.

Rust verification passed under the shared Cargo lock and required resource
limits: workspace formatting, all 444 `pumpkin-core` library tests, core Clippy
with all targets/features, and the debug server build. The existing
`proc-macro-error2` future-compatibility warning remains.

Limits: headless protocol and server-state observations only. No rendered
client, full boss fight, Bedrock, reload, dispenser or wall-skull proof.
The focused regression uses real scratch worlds; no new isolated Rust unit
test was added. Initial spawn position and rotation are separate candidates.

For a real-client follow-up, place the final floor skull on a valid soul-sand
T in Peaceful and confirm all seven blocks remain and no Wither appears.
Switch to Easy, remove and replace that skull, and confirm construction occurs.
Capture a recording of both placements and the difficulty changes before any
upstream submission. No upstream PR is opened by this campaign.
