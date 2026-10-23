# Dragon breath damage attribution

Assignment 83 corrects missing damage attribution in both sitting dragon flames
and dragon-fireball impact clouds. The owner UUID is retained on the cloud and
resolved to a living entity when damage is applied. Instant damage now uses
indirect magic with the cloud as direct source and the dragon as cause. The
existing damage plugin events and combat tracking receive that context.

The damage broadcaster previously passed direct source and cause to the Java
packet constructor in reverse order. Its single caller is LivingEntity's damage
path. The packet mapping now preserves those roles for all living damage events;
nonentity damage keeps its empty IDs. A Rust regression compares payload bytes
with the official 26.3 cloud event, including the ownerless case.

Vanilla references: DragonFireball.onHit and DragonSittingFlamingPhase.doServerTick
set the cloud owner; AreaEffectCloud.serverTick passes the cloud and its resolved
owner to HealOrHarmMobEffect.applyInstantaneousEffect. That method selects indirect
magic whenever a direct source is present, including ownerless clouds. Owner NBT
uses the existing UUID codec. Other potion callers retain their existing wrapper
and empty damage context. Lingering-potion owner assignment is a separate lead.

Baseline reproduction used campaign 82 (7e511560259b82d69eda457e56a592a30a6178b2)
and an isolated official 26.3 server with a headless protocol-777 observer. In two
trials of owned, unowned and unresolved-owner fireballs plus sitting flames,
vanilla damage events have type 23 and the cloud direct ID; owned clouds also
have the dragon cause ID. Baseline Pumpkin uses type 27 and empty entity IDs.
Victim health loss agrees. The final comparison also checks the real victim's
`execute on attacker` relation and runs dragon-breath-attribution.json.

Validation: all 495 pumpkin-core library tests, workspace formatting, core
all-target/all-feature Clippy and debug server build passed under the shared Cargo
lock with one build job, no incremental/debug info, and the required resource
caps. Restoring the old reversed packet mapping makes the new Rust regression
fail with the expected payload assertion; the corrected mapping passes.

The identical final headless probe passes 99/99 applicable checks on official
26.3 and 100/100 on the final-source binary (the extra check verifies its binary
hash). Campaign 82 passes 71/100 and fails exactly 29 attribution checks; health,
entity-presence, observer, cleanup and shutdown controls pass. All six observations
in the committed scenario pass on vanilla and final Pumpkin, while baseline
fails its four owner/attacker observations. Per-case commands, probe and scenario
hashes agree. Logs are free of errors and panics. Raw reports, packet logs, hashes
and the strict comparator are retained in the deployment workspace's
`artifacts/christine-dragon83-live-validation.json`. The Rust source hashes match
the built files. Current upstream was checked for the same missing owner flow and
reversed packet mapping; no separate upstream binary was built.
This document does not claim rendered-client, Bedrock or whole-fight parity.
No installed plugin, player death/kill-credit, player difficulty scaling, knockback,
undead heal/harm inversion, full
cloud lifetime or save/reload behavior has been exercised. Owner UUID persistence
is implemented; the cloud's broader preexisting persistence gaps remain separate.
The packet mapping correction affects other damage callers, while dedicated
runtime coverage here concerns dragon clouds. Initial wall-impact probes placed
victims inside the wall and were superseded by clearing that wall before contact.
The final fixture releases NoAI before cleanup to avoid a separate corpse-removal
issue. Upstream overlap searches inspected PRs 3407, 3661, 3694, 3835, 3663 and
3816; none implements this cloud owner/damage chain. Fork master was already an
ancestor of the campaign branch when fetched; no merge was necessary.
