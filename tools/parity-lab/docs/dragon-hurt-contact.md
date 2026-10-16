# Ender Dragon hurt contact suppression

Vanilla 26.3 `EnderDragon.aiStep` wraps wing push and head/neck damage in
`!wasHurtRecently()`. `LivingEntity.wasHurtRecently` checks `hurtTime > 0`.
A normal accepted hit sets that timer to 10, separately from the twenty-tick
`damageCooldownTime`. A stronger hit during the protected half of the damage
cooldown deals the difference without restarting the animation. The base tick
decrements the animation before dragon AI. `HurtTime` NBT persists only the
animation timer, not damage immunity.

Pumpkin originally applied contact effects throughout that interval and used
its damage cooldown for HurtTime. The correction introduces the separate living
hurt animation timer, initializes it only in the existing new-hit branch,
counts it down, resets it on respawn, and reads/writes it as HurtTime. The dragon
contact filter uses this timer for both push and damage. Pumpkin runs mob AI
before its living tick, so a stored animation time of 1 permits contact on that
tick, matching vanilla's pre-AI countdown. Creative and spectator exclusions
remain part of the filter.

Fresh upstream master `5b53f06` and fork master `65bca3f` were fetched; fork master
is already an ancestor. Open PRs 3407 and 3661 cover multipart hitboxes, damage
routing, crystal healing and fight state. PRs 3793 and 3794 concern velocity and
player touch; PR 4080 adds team damage rules. No matching timer gate or separate
hurt animation timer was found in the inspected dragon/living patches. Leads:
[Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468),
[parity tracker](https://pumpkinmc.org/tracker/).

The new Rust boundary regression fails with the original ungated eligibility.
With the correction, all 451 pumpkin-core library tests, workspace formatting,
core all-targets/all-features clippy and the full Pumpkin binary build pass.
Cargo ran under the shared lock, one job, disabled debug info/incremental, and
MemoryMax=5G, MemorySwapMax=0, CPUQuota=200%. The existing proc-macro-error2
future-compatibility warning remains.

The source commit is `a5ab6b8`. Both Rust files match the recorded pre-build file
hashes and source diff. The immutable binary SHA-256 is
`72e293c4703bbb0ba322938d63bed0cab3701742c58cb7488e8d7e18985776a9`.
The build record identifies the parent commit plus source diff; a supplemental
provenance record covers both changed Rust files.

Settled isolated arena comparisons use a connected protocol-777 headless player,
one dragon per sample, Resistance to isolate impulse, frozen/stepped ticks,
and mob griefing disabled. Each target has two repetitions of an undamaged
control and samples after zero, eight, nine and ten ticks since a successful
player-attributed hit. Vanilla suppresses all four samples before expiry and
pushes in all six controls/expiry samples. Baseline pushes in the four samples
where vanilla suppresses contact. Its HurtTime also exposes the old twenty-tick
damage timer. The settled replay avoids two early timer reads in the initial
exploratory baseline, which is retained separately.

The patched target matches all ten vanilla contact decisions: four suppressed
samples and six positive controls, including the exact 1-to-0 expiration tick.
HurtTime values and countdowns also match. All thirty samples across the final
vanilla/baseline/patched runs have verified exact starting positions, clock
deltas, successful hit health reduction where applicable, and dragon absence
before spawning the next sample. Fixture commands are identical apart from
clock polling.

A separate timer lifecycle replay passes five checks on both vanilla and the
patched server: a first hit starts HurtTime at 10; an equal hit eight ticks later
is blocked; a stronger hit at that point reduces health without restarting the
remaining HurtTime of 2; subsequent ticks produce 1 then 0; a hit after the
immunity window starts a new HurtTime of 10. Both targets record the same timer
sequence `[10, 2, 2, 2, 1, 0, 10]`. The damage amounts themselves still differ
because part-specific incoming damage routing is outside this patch.

All five final scratch servers stopped cleanly and their console logs contain
no ERROR or panic lines. Raw known scoreboard delimiter errors and unsupported
DragonPhase NBT observations are retained; those observations are not used to
establish phase behavior. Main validation compares impulse suppression/resumption,
not raw Motion equality across different player physics implementations.
Resistance intentionally prevents an independent contact-health-damage test.

Evidence records: local artifacts/christine-dragon12-rust-validation.json,
christine-dragon12-source-provenance.json, christine-dragon12-live-validation.json
and christine-dragon12-timer-validation.json. Task-local raw reports, source
inspection and checks remain under local artifacts/christine-dragon12-*;
logs, worlds and downloaded/decompiled code are not published.

Limits: this changes the hurt-time gate on the existing contact query. Wing,
head and neck volumes, multipart registration, perched contact, nonplayer
victims, team rules, the victim's two-tick damage gate and complete boss fights
remain separate work. Reload/respawn paths were reviewed in source but not
independently exercised. The headless protocol client establishes server state,
not visual or prediction parity.

Human play-test checklist: approach an airborne dragon in survival, damage it,
and stay in wing contact. Expect a brief pause in contact push while it flashes
red, then resumed push when the flash ends. Record the hit, flash, pause and
resumed contact from a real client before any upstream submission.
Capture: <attach screenshot or recording here>
