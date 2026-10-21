# Wither XP after tamed wolf damage

An owned wolf damages a Wither and another damage source finishes it within
100 living-entity ticks. The official 26.3 server drops experience; campaign73
Pumpkin does not. The same difference occurs when the wolf delivers the lethal
hit and when the owner is offline. The baseline reproduction checks ownership,
actual health changes, star drops and the connected player before interpreting
missing experience as a source defect.

The Rust correction extends the existing mob XP memory to accepted tamed-wolf
hits, matching `LivingEntity.resolvePlayerResponsibleForDamage`. An owned wolf
refreshes memory to 100 ticks without requiring the owner to be online; a tame
wolf with no owner clears memory. Wild wolves, cats and other attackers leave
memory alone. The existing boss immunities, damage guards and hurt cooldown run
before this update, and lethal damage processing runs after it. This changes
shared living code because Wither inherits its XP rule. The other lane reserves
`world/dragon_fight.rs`; this lane reserved `entity/living.rs` before editing.

This bounded change concerns mob XP eligibility. Existing kill attribution,
loot predicates, death messages, orb values and the reward calculation are
separate behavior. No broad attribution rewrite or other wolf AI change is made.

The committed `fixtures/wither-wolf-xp/cases.json` and
`tests/check_wither_wolf_xp.py` cover two trials of online/offline owners, ticks
99/100, wild wolves, an owned cat, player-memory refresh/preservation, a rejected
cooldown hit, a lethal wolf hit and a sheep control for another shared caller.
The private runner reuses existing isolated arena, tick-control, console/RCON
and protocol 777 client support. Every target uses a fresh disposable world and
keeps a headless client connected. The checker reads actual health, ownership,
XP selector and orb-NBT responses; it checks cleanup and stopped server processes.
For the online-owner setup, only the literal runtime player UUID is normalized
when comparing command hashes. Its equality with the wolf owner is checked
separately. Other gameplay commands must match exactly.

Fork and upstream master were fetched; fork master is already an ancestor of
this campaign branch, so no integration commit is required. The tracker and
Mob AI issue #3468 were consulted. The invulnerability goal lead is already fixed
and was not repeated. Open PRs were checked: #4107 changes combat timestamp sources,
while #4120, #4080 and #4092 change other shared living code. None implements this XP
rule. Existing overlaps for Wither flight/regeneration, star death handling,
projectile effects, targeting, knockback and sound categories remain deferred.

All 450 core Rust library tests, workspace formatting, core Clippy with all
targets/features, and a debug server build passed under the shared Cargo lock,
one build job, disabled debug info/incremental compilation and the required
5 GiB/no-swap/200%-CPU scope. The existing proc-macro-error2 future-compatibility
notice remains.

The final comparison passes 306/306 checks on both vanilla and the patched
binary. The campaign73 baseline passes 294/306, failing exactly the twelve
expected owned-wolf XP checks: online owner, offline owner, tick 99, refreshed
player memory, a lethal wolf hit and the shared sheep control in both trials.
Normalized gameplay hashes match across all three targets. The source and binary
hashes match the validated build; the committed source is verified again before
recording publication. All three scratch processes stopped after cleanup.
Console and client logs contain no ERROR, panic or uncaught-thread-exception
lines. These bounded results establish the selected XP correction only.

The initial probe tried a `data modify ... set from entity @p UUID` setup command
that Pumpkin rejects. It was replaced by the existing `data merge` command with
the queried literal UUID, and all final target runs use that setup. The failed
setup run is excluded. The checker accepts either a zero-health Wither or an
immediately removed Wither after lethal damage, and asserts XP separately;
it does not turn an existing removal-timing difference into the selected bug.

No rendered-client, natural wolf melee, whole boss fight, Bedrock or plugin
listener proof is claimed. Command damage exercises actual Wither immunity,
living damage and death paths but does not prove wolf attack-goal behavior.
XP presence is verified, not orb amount or collection. Save/reload of player
memory and the ownerless-tame edge case are source-reviewed only. The baseline
is the campaign73 binary; current upstream's missing credit path is checked in
source, without a separately built upstream-master server.
