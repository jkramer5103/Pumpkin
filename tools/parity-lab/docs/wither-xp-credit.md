# Wither death XP credit expiry

A player damages a Wither, waits 100 entity ticks, and an environmental damage
source finishes it. Vanilla drops no experience. Pumpkin still drops XP at
100 and 101 ticks and with daylight time paused. A fresh kill and a kill at
99 ticks drop XP on both. These differences were reproduced on the official
26.3 server and the clean campaign 72 binary before editing Rust.

Mob death XP now uses a separate 100-tick player-damage memory, matching
`LivingEntity.resolvePlayerResponsibleForDamage`, `baseTick` and `dropExperience`.
Accepted player hits refresh it after the existing damage/cooldown guards and
before death processing. Living ticks decrement it, including NoAI mobs. Combat
history and kill-credit timestamps no longer decide mob XP eligibility. The
existing mob-drops rule, reward calculation, orb spawning and plugin death events
remain in the same path. Other living entities retain their existing XP gate.
Loot-table player-credit predicates and death-message attribution are separate
existing behavior; this patch does not change them.

The implementation is in shared living code because Wither inherits this rule.
The other lane reserves only `world/dragon_fight.rs`; `entity/living.rs` was
reserved before editing. The same focused fixture covers sheep deaths to check
another caller. No Wither AI or movement change is needed.

The committed `fixtures/wither-xp-credit/cases.json` and
`tests/check_wither_xp_credit.py` cover two trials of uncredited, fresh, tick 99,
tick 100, tick 101, daylight-paused, time-command and shared sheep deaths. A
connected protocol 777 headless client keeps each disposable arena ticking.
The checker validates the command streams, actual XP selectors and orb NBT,
initial health, boss drops, player presence, cleanup and stopped server processes.
There is no rendered-client or whole-fight evidence. The time-command control
is required to remain credited; it also passes on the baseline because the
combat history can supply the player credit.

Fork master and upstream master were fetched before selection; fork master is
already an ancestor. The tracker and Mob AI issue #3468 were consulted. The
spawn-invulnerability goal is already completed and was not repeated. Open
PR #4107 changes existing kill-credit timestamps to world age, but leaves the
combat-history XP gate intact; this patch changes neither those timestamps nor
`get_kill_credit`. PR #4105 concerns mob loot gating; PR #3865 concerns star death
handling. PR #3835's projectile damage/effect work and PR #3988's ambient foundation
were excluded as overlapping leads. No upstream write was made.

All 450 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed with the shared Cargo lock, one build
job, disabled debug info/incremental compilation and the required 5 GiB/no-swap/
200%-CPU scope. The existing proc-macro-error2 future-compatibility notice remains.

The final identical-input comparison passes 144/144 checks on vanilla and the
patched binary. Campaign72 baseline passes 136/144, failing exactly eight XP
expiry checks: tick 100, tick 101, paused-daylight tick 101 and shared sheep tick 100,
each in two trials. All three targets advance 1,635 controlled ticks and use
identical gameplay-command hashes. Source and binary hashes match the tested
build; committed source is checked again before publication. The final console
and client logs contain no ERROR, panic or uncaught-thread-exception lines.
Both Pumpkin processes completed saving and stopping. Vanilla stopped after
saving began; full-save completion is not established within the shutdown grace.

An initial checker expected Value NBT on experience orbs. Pumpkin omits that
field, so the corrected checker verifies the actual orb NBT response and XP
presence. It does not claim XP amounts, collection or NBT-value parity. The
initial seven-case probe is supporting reproduction only; the final eighteen
cases are the matched comparison. No gameplay input changed when correcting
the checker.

Player death XP rules, tamed-wolf credit, save/reload memory, shield/absorption
edge cases, other mobs, Bedrock, plugins and natural boss fights are not
established by this bounded fixture. The baseline is the campaign 72 build;
current upstream was checked in source, without a separate upstream-master
binary comparison.
