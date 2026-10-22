# Dragon respawn abort resets overlapping pillar crystals

`DragonFight::reset_spike_crystals` tested each crystal's center against a pillar
box. Vanilla `EnderDragonFight.resetSpikeCrystals` queries `EndCrystal` hitboxes
intersecting that box, then clears invulnerability and the beam. A crystal moved
slightly outside the minimum X/Z boundary can still overlap the pillar query.
Aborting the ritual should make that crystal damageable and clear its beam.

The source correction uses the existing world hitbox query. Both abort and
successful ritual completion call this method. Other crystal counting/spawning
queries and the shared spike bounding-box definition are unchanged; the latter
has separate maximum-edge and vertical-bound discrepancies requiring another
bounded reproduction.

Workspace formatting, all 493 core Rust library tests, all-target/all-feature
core Clippy, and the debug server build passed under the shared Cargo lock and
resource limits. The existing `proc-macro-error2` future-compatibility notice
remains. The identical-probe comparison passes all 12 samples on official vanilla
26.3 and patched Pumpkin. The campaign-76 baseline differs at exactly four
overlapping samples; all eight other samples agree. The fixture and report checker
cover six offsets on each of two regenerated pillar crystals, including exact-touch
and outside
controls. Each trial starts a real item-triggered ritual, advances 185 controlled
ticks, moves the two naturally invulnerable crystals to the query boundary, and
aborts by applying explosion-type damage to a ritual participant. Explosion-type
damage suppresses secondary crystal explosions. The probe checks immunity before
abort, damage acceptance and removal afterward, and tracked beam metadata. It
clears fire from the fourth placement space between trials. Initial incomplete
runs without that setup correction, preliminary integer-centered touch controls,
and one vanilla watchdog failure are excluded. The final probe uses explicit
decimal teleport coordinates, confirms actual positions, and checks player and
ritual participant presence in every trial. Participants use `PortalCooldown:1000`.
All three complete final reports pass
position, immunity, beam, damage/removal, ritual participant, player/client, cleanup
and stopped-process controls. Source, baseline/fixed binary, official source/jar,
probe, fixture/checker, report, packet and six server/client log hashes were
verified. Logs contain only known startup warnings. Each trial advances exactly
185 regeneration ticks; arena initialization needs one extra tick on Pumpkin.

Both X and Z boundaries have the following observed outcomes. Offsets are from
the minimum pillar bound; crystal width is two blocks.

| Center offset | Vanilla / patched reset | Baseline reset |
| --- | --- | --- |
| -0.5 | yes | no |
| -1.001 | no | no |
| -1 (touch only) | no | no |
| -0.999 | yes | no |
| 0 | yes | yes |
| 0.5 | yes | yes |

Official source references, kept outside Git: 26.3 `EnderDragonFight` abort/reset
methods, `EndSpikeFeature.EndSpike` bounds, `EntityGetter.getEntitiesOfClass`, and
`EndCrystal.hurtServer`. Refreshed upstream source retains the center test. Open
PRs #3407/#3661 concern multipart hitboxes/combat and #3694 crystal combat; their
reviewed patches do not replace this reset query. The fork master is already an
ancestor of the campaign branch. No upstream PR or issue was created.

Limitations: headless protocol and server-state evidence only. No rendered-client,
Bedrock, successful full ritual, reload, or whole-fight proof. Crystal positions
are moved by commands after natural regeneration, and radii/heights adapt to the
actual arena. This task samples minimum X/Z edges at Y=120, where the existing
query bounds agree with vanilla; maximum/vertical bounds remain a separate lead.

For a human play test, start a respawn ritual in an isolated End arena, move a
new pillar crystal just outside a pillar's minimum X/Z edge while its hitbox
still overlaps, then destroy a portal ritual crystal. Expect the moved crystal's
beam to disappear and an ordinary attack to destroy it. Also check that a crystal
whose hitbox only touches the boundary keeps its beam and invulnerability.
Capture both outcomes in a real-client recording before any future upstream PR.
