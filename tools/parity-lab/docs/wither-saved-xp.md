# Wither experience credit survives entity NBT restoration

A Wither recently damaged by a player loses its XP eligibility when restored from
Pumpkin's serialized entity NBT. Vanilla retains the remaining credit window,
including credit from an owned wolf whose owner is offline. This changes actual
XP drops after restoration, independently of how the final damage is attributed.

`LivingEntity` now retains the responsible player's UUID alongside the existing
100-tick memory. It saves and restores `last_hurt_by_player` and
`last_hurt_by_player_memory_time`, uses the wolf owner's UUID for qualifying wolf
hits, and clears the reference on the tick after the timer reaches zero.
Missing saved fields reset the memory, as vanilla does. Existing runtime combat
IDs, kill attribution and loot predicates are outside this change.

The reference is the official 26.3 server's `LivingEntity`:
`resolvePlayerResponsibleForDamage`, `baseTick`, `addAdditionalSaveData`,
`readAdditionalSaveData`, and `dropExperience`. Current fetched upstream lacks
this persistence. Open upstream PRs were checked: #4107 changes attribution and
combat timestamps, #3720 supplies generic plugin NBT transport, and #4092 and
#4131 change movement/damage sources and attack events. None implement this rule.
The fork master is already an ancestor of this campaign branch.

Focused coverage in `fixtures/wither-saved-xp/cases.json` and
`tests/check_wither_saved_xp.py` uses two trials each for Withers and sheep:
uncredited, immediate player credit, player credit at tick 99/100, already
expired credit, offline-owner wolf credit, and wolf expiry after restoration.
The private probe reads the actual complete entity SNBT, removes only its UUID,
removes the original entity and drops, and recreates the entity with that exact
payload. It then kills the restored entity with unattributed damage and checks
XP presence and the Wither's nether star. Health, new identity, accepted hit,
remaining time, offline owner, verified tick stepping, client survival, cleanup,
and stopped-process controls prevent an empty or failed setup from passing.
The checker compares commands across targets while normalizing only each
server's verified saved payload and its saved-health assertion.

Validation: all 450 `pumpkin-core` library tests, workspace formatting,
`pumpkin-core` all-target/all-feature Clippy, and the debug server build pass
under the shared Cargo lock with one build job, debug info and incremental
compilation disabled, and the required resource limits. The existing
`proc-macro-error2` future-compatibility notice remains.

Official 26.3 and patched Pumpkin each pass 428/428 focused checks. Campaign 74
passes 348/428: its 80 failures are confined to saved/restored credit fields,
offline-owner references and 12 missing-XP cases across both trials. Tick 99
retains credit; tick 100 expires it after restoration. Fresh and previously
expired mobs remain uncredited. All three runs use identical probe/fixture
hashes and matching commands under the documented normalization. Source,
binary and checker hashes are verified, and all six server/client logs contain
only known startup warnings with no errors. An initial control incorrectly
assumed unarmored damage and is excluded; final runs check each actual saved
health. Private report: `artifacts/jaron-wither75-live-validation.json`.

The shared NBT hooks are used by all living entities. This patch adds only the
UUID and countdown persistence; the existing wolf-credit countdown now uses a
single owner lookup while retaining the ownerless clearing behavior. The timer
still governs mob XP alone. The UUID is forgotten on the tick after the counter
reaches zero, matching vanilla's ordering.

This is headless server-state evidence of entity serialization and recreation,
not a disk restart, chunk-unload/reload, rendered client or whole boss fight.
XP presence is checked; exact orb value, collection, natural wolf melee, Bedrock,
plugins and broader loot/kill attribution are not claimed. No upstream-master
binary was built separately; fetched upstream was checked in source.
