# Dragon respawn crystal hitboxes

Pumpkin selected ritual crystals using a symmetric distance from each ritual
cell. A crystal whose base was one block above the cell still participated;
one whose top overlapped the cell from below could be missed. Vanilla 26.3
`EnderDragonFight.tryRespawn` queries crystal hitbox intersections with the
one-block cell. The correction uses Pumpkin's existing bounding-box query and
retains every matching crystal, the four required positions and the existing
fight-state gates.

The focused regression fixture covers eleven vertical positions, including
touching and just-overlapping boundaries, three ordinary participants and a
nearby uninvolved crystal. The official server selects crystals at relative
heights -1.999, -1.5, -1.499, 0 and 0.999; it excludes -2.001, -2, 1, 1.499,
1.5 and 1.501. The baseline source instead uses `abs(y - cell_y) < 1.5`.
The accompanying checker validates individual crystal IDs and beam metadata,
actual fourth-position item use, five controlled observation ticks, initial
dragon creation/removal, player/client presence, cleanup and process shutdown.

The arenas use the real killed-fight portal and isolated scratch worlds. Initial
crystals are summoned; the final position is filled by a headless protocol
client using the crystal item. Summoned crystals have a portal cooldown of 1000
ticks, and every candidate is confirmed present before item use. An exploratory
run without that cooldown let low crystals enter the active portal; those
confounded lower-edge results are excluded from the regression evidence.

The baseline and official-server comparisons passed their expected controls;
Pumpkin differs from vanilla at four of the eleven vertical positions. Workspace
formatting, all 493 Rust library tests, core all-target/all-feature Clippy and
the debug server build passed under the shared Cargo lock with the required
resource limits. The identical patched-server arena comparison matches vanilla
at all eleven vertical positions and preserves the three ordinary participants
and the uninvolved control. Individual membership matters: both servers beam
eight crystals, but the baseline selects four incorrect members. The first
patched attempt failed before the initial fight dragon spawned and never
reached the ritual; it is excluded. The unchanged probe succeeded in a fresh
scratch world. Source, binary, probe, fixture, checker, packet and server/client
log hashes were verified. Logs contain only known startup warnings; the existing
`proc-macro-error2` future-compatibility notice remains in Cargo output.

The source and open PRs were inspected against upstream master
`9c04f714bb7eb26579c652f9744895d465ee902b`. PRs 3407, 3661 and 3694 cover
other dragon/crystal areas, not this ritual-cell predicate. Fork master
`65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an ancestor of the
campaign branch. Upstream retains the faulty position predicate; no separate
upstream-master binary was run.

Evidence is headless server/protocol state only. It does not verify rendered
beams, Bedrock, reload behavior, ritual completion or an entire boss fight.
For a human client check, prepare a killed-fight End arena, place three normal
ritual crystals, and position additional north crystals just below and above
the ritual cell with portal cooldown set. Place the fourth crystal using its
item; expect beams only from hitboxes that overlap the cells. Capture a recording
of the low and high boundary cases before considering upstream submission.
