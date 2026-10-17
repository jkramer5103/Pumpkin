# Dragon corpse ascent

Dragon corpses now rise throughout their 200-tick death animation, including
with NoAI. Previously, a zero-health dragon near the podium froze with NoAI and
both AI modes lost the corpse at tick 20 through ordinary living removal.

The dragon handles zero-health death ticks before living AI. Its dying-flight
phase remains separate, so flight steering cannot restore corpse health. Corpse
ticks move the dragon and its parts directly using the vanilla float-valued
upward delta. Shared living code exempts only dragons from ordinary corpse
travel and removal after 20 ticks. The existing death event, XP and fight
completion code remains in the corpse sequence; final XP uses the position after
movement. Live AI and corpse ticks share the existing fight-bar update.

The reference is Minecraft 26.3 `EnderDragon.aiStep`, `EnderDragon.tickDeath`
and `DragonDeathPhase.doServerTick`. From Y80, vanilla reaches
84.00000005960464 at tick 40 and 99.90000029653311 at tick 199.

Two trials for each NoAI value, plus the published regression fixture and
ordinary-cow corpse controls, produced vanilla 93/93, baseline Pumpkin 41/93 and
patched Pumpkin 93/93 focused checks. Baseline failures are confined to dragon
corpse movement and zero-health presence after tick 20. Patched dragons remain
at zero health, rise at every sampled tick and disappear at tick 200. Cow
corpses still disappear at tick 20. Source, binary and fixture hashes, equal
stimuli, exact tick barriers and error-free feature logs were checked.

All 458 core library tests, workspace formatting, core all-targets/all-features
clippy and a debug server build passed under the shared build lock with one
Cargo job, no debug info/incremental compilation, MemoryMax=5G,
MemorySwapMax=0 and CPUQuota=200%. The existing proc-macro-error2
future-compatibility warning remains.

The fixture is `lab/examples/dragon-death-ascent.json`. Raw evidence is retained
outside Git in deployment artifacts `christine-dragon19-live-validation.json`,
`christine-dragon19-rust-validation.json` and
`christine-dragon19-source-provenance.json`. The initial selector probe excluded
dead entities and is discarded. Earlier fixture expectations assumed identical
float spelling; final health assertions compare NBT values through UUID and @s.
Only the valid cow controls from those earlier supplemental runs are included.

Fork master 65bca3f is already integrated. Upstream master 998c3f8 has no changes
to the affected dragon or living files since the original review at b57d821.
Open PR3407 at a0cb2be covers parts, damage and healing; PR3661 at e7e5449 covers
part lookup/removal. Their inspected diffs do not supply this corpse correction.
No upstream PR code was copied.

Limits: headless protocol 777 server-state evidence, without rendered-client
capture or a complete boss fight. Forced zero health isolates corpse animation;
natural dying-flight entry, portal activation, save/reload and part rendering
remain unproven. All nine scratch servers stopped; six Pumpkin runs logged
completed shutdowns, while the three vanilla runs logged world saving without
a verified completion marker within the existing eight-second harness grace.
For a visual check, use the fixture's lethal-hit/zero-health setup in an isolated
arena and verify continuous ascent until removal, with either NoAI value.
