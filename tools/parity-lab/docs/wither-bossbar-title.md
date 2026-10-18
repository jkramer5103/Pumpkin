# Wither bossbar name updates

A tracked Wither keeps its old bossbar title after its custom name changes. Java 26.3 immediately sends `UPDATE_TITLE` on the existing bar UUID, including text style and entity display-name metadata. It does this while simulation is frozen and with `NoAI:1b`. Reloading the same component does not send a title update.

The fork now notifies spawned mobs when `Entity::set_custom_name` changes the component. The default mob hook does nothing; Wither sends its current display name to existing bar viewers through the existing Java/Bedrock title-update helper. Named initial bars also use the display name, preserving hover/insertion metadata. Existing metadata writes, tracking reconciliation, progress updates and lifecycle scheduling remain intact. Names assigned before spawning are sampled when the bar is added.

Reference: local official 26.3 `WitherBoss.setCustomName`, `readAdditionalSaveData` and `ServerBossEvent.setName`. The tracker and issue 3468 are leads only. Open upstream PR4092 covers separate AI/lifecycle changes and PR3717 covers entity-name metadata loading; neither contains this Wither title correction. Fork master was fetched and is already an ancestor. New upstream unrelated commits were not integrated.

## Regression and validation

`lab/examples/wither-bossbar-title.json` defines a bounded, loaded, creative-player arena and one charging Wither. An external protocol 777 headless client checks initial named ADD, rename to red Second, identical-name reload, restyle to blue, and rename to Paused with NoAI. The simulation remains frozen throughout mutations; health 300 and Invul 194 are controls. Packet checks require the existing bossbar UUID, one title update for each changed component and no ADD/REMOVE replacement. Command-only fixture execution cannot validate the title packets.

Final identical-fixture two-trial comparison: vanilla and patched pass 88/88 checks; baseline 5715eab passes 68/88. Baseline misses all six changed-title updates and initial display-name metadata. The twenty failed assertions include repeated initial metadata controls and style checks on missing updates; they are not twenty independent defects. Patched sends one update for each of the six mutations; both identical-name reloads send none. Frozen health/invulnerability, stable bar UUID, style/hover/insertion, no replacement, client survival and cleanup controls pass. All final processes stopped; both Pumpkin logs show completed saves/stops without errors or panics. Vanilla RCON shutdown is verified; complete save is not.

Rust validation under the shared Cargo lock, one build job and required memory/CPU caps: all 444 existing core library tests, workspace formatting, core all-targets/all-features Clippy and the debug server build pass. Focused regression coverage is the packet fixture; no new Rust unit test was added. Source/binary hashes and measured command/fixture hashes match. The existing proc-macro-error2 future-compatibility warning remains.

Local evidence: `artifacts/jaron-wither42-validation.json`, `artifacts/jaron-wither42-verify.json`, `artifacts/jaron-wither42-source-provenance.json` and the associated raw server/client packet reports. These runtime artifacts are excluded from the fork commit.

## Limits

No rendered Java or Bedrock client, visual bossbar, name-tag interaction, multiplayer, actual world reload or full boss fight was tested. The notification is reached by the shared setter used by NBT and name tags; live interaction must still be checked. CustomName removal and inheritance of omitted nested component style during data merge are existing shared NBT behaviors outside this change. The final fixture specifies styles explicitly to isolate bossbar notification. NoAI audience/lifecycle scheduling and passive-heal progress ordering remain separate and overlap PR4092.
