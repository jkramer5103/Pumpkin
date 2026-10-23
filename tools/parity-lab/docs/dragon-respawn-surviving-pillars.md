# Dragon respawn with surviving pillar crystals

Respawning a dragon while an original pillar crystal survived could stop the
world at the first pillar explosion. The stage cleared the pillar cap and called
`World::explode` while holding the dragon fight mutex. Explosion damage removed
the original crystal and its damage callback attempted to lock that same mutex.

The stage now returns a pending pillar action. The outer fight tick releases its
mutex before clearing the cap, exploding it and rebuilding the pillar. This keeps
the ordering in official 26.3 `DragonRespawnStage.SUMMONING_PILLARS.tick`, including
synchronous crystal destruction notification before the replacement is spawned.
The existing final-stage crystal consumption also runs after the lock is released.
Only `world/dragon_fight.rs` changes; shared crystal damage and explosion behavior
are outside this patch.

The focused regression fixture in `fixtures/dragon-respawn-surviving-pillars/`
and checker in `tests/check_dragon_respawn_surviving_pillars.py` retain ten original
pillar crystals, kill the natural dragon and start a real item-triggered ritual.
Twenty-tick samples check each original crystal being replaced, total crystal
counts, portal crystal consumption, the healthy dragon, pillar vulnerability and
continued world ticks. A headless Java client sends the fourth crystal placement.
The final probe verifies all 49 central End chunks are loaded before the fight.

Campaign85, built from d273345d047b8fe91066f65b003ffe1f7917af25, completes 140
controlled ritual ticks, then stalls at gametime 474 during the first pillar
rebuild. The next requested 20 ticks never finish and the tick controller times out.
The incomplete report is retained and the scratch server is forcibly terminated.
Its immutable binary hash matches the preceding task's Rust build record. Current
read-only upstream has the same lock-held pillar explosion; no standalone upstream
binary is built. The open dragon hitbox and crystal combat fixes reviewed do not
change this stage.

All 495 core Rust library tests, workspace formatting, core Clippy with all
targets/features and the debug server build pass under the shared Cargo lock and
resource limits. The existing `proc-macro-error2` future-compatibility warning
remains. The focused checker rejects the unpatched report as a regression.

Final baseline and patched runs use the same probe and headless client. Vanilla
and patched Pumpkin complete 620 ritual ticks, replace all ten original crystals,
consume all four portal crystals and leave one 200-health dragon plus ten
vulnerable pillar crystals. Damage/removal checks and another 40 world ticks
pass. The baseline stops at the first pillar rebuild after 140 requested ritual
ticks. All 47 baseline/fixed stimulus commands from original-crystal tagging
through the stalled step match, excluding only clock polling. Successful server
and client logs contain no error or panic lines; client/player, placement-packet,
cleanup, process-stop and dragon-tracking checks pass.

One selected trial per target supports these results. Other exploratory runs,
setup failures and quota-interrupted runs are excluded. The final scratch client
adds a stationary position packet after teleport confirmation, which drives
Pumpkin chunk streaming; readiness retries can advance one setup tick. Baseline
and patched Pumpkin use both changes. The successful vanilla reference uses the
original client and probe with identical ritual logic; a later vanilla trial with
the extra movement packet disconnects before setup and is excluded. Probe,
fixture, checker, source, immutable binary, official jar, reports and packet/server/
client log hashes are recorded in the task's runtime validation artifacts.

Headless protocol/server-state observations provide no rendered-client, Bedrock,
save/reload, arbitrary arena, plugin interaction or whole-fight proof. The ritual
is sampled every 20 ticks, so exact single-tick stage timing is not asserted. Empty
beam-NBT queries are excluded as evidence. General explosion source exclusion and
crystal combat behavior remain separate.
