# Overlapping dragon respawn crystals

A dragon respawn ritual includes every End Crystal whose hitbox overlaps each
of the four portal positions. Pumpkin previously retained only the first crystal
at each position, leaving additional eligible crystals without ritual beams and
outside the fight's participant list. The Rust change collects every match and
still requires at least one crystal at each position.

The reference is official Minecraft Java 26.3 `EnderDragonFight.tryRespawn`:
`getEntitiesOfClass` returns a list per position and `addAll` retains all of it.
The existing Pumpkin position predicate is unchanged. Its vertical bounds remain
a separate candidate; this patch only fixes participant multiplicity.

## Reproduction and regression

The isolated End arena kills the initial fight dragon, finds the actual exit
podium, and clears crystals. It summons three crystals north, two south, and one
west. A headless protocol client places the east crystal with the actual item.
A crystal three blocks farther north is a nonparticipating control. The frozen
server advances exactly five observation ticks, before pillar regeneration.

The comparison uses decoded spawn and metadata packets to associate every crystal
with its position and count central ritual beams. Vanilla sends seven beams.
Campaign 74 sends four: one for each position. Both pass the ordinary-crystal,
actual item-use, player/client, tick-count, cleanup and stopped-server controls.
The fixture and checker cover the complete eight-crystal packet set, including
both clusters and the ordinary one-crystal west/east controls.

The patched build sends all seven beams, matching vanilla in both clusters and
the single-crystal controls. All 493 core Rust library tests, workspace formatting,
core all-target/all-feature Clippy, and the debug server build passed under the
shared Cargo lock with the prescribed resource limits. The identical probe hash
was used for all three targets. Source, binary, packet, fixture/checker and six
server/client log hashes were verified. Logs have only known startup warnings;
the existing proc-macro-error2 future-compatibility notice remains.

Current upstream retains the first-match selection. Refreshed open dragon and
respawn PR searches and the relevant crystal-combat/dragon-part patches show no
overlapping participant-selection change. Fork master is already an ancestor;
no integration changes were needed. The sole caller is EndCrystalItem, whose
item-use behavior remains unchanged. The complete selected list now feeds the
existing beam, crystal-destruction, and respawn-stage paths.

A preceding cage-direction lead was disproved: saved chunks in both servers have
all 146 expected final iron-bar states after regeneration. Neighbor updates repair
the reversed constructor properties. No cage source edit is included. Pumpkin
rejects property filters in `execute if block`; those command errors were excluded
from gameplay evidence and actual saved chunks were inspected instead.

## Scope and limitations

This is headless server/protocol evidence. No rendered-client, Bedrock, reload,
full ritual completion or whole-fight proof is claimed. Later abort/consumption
of additional participants is not independently asserted. Initial placement uses
commands for overlapping crystals; the fourth placement uses the real item.
Portal heights vary, so the probe adapts to the discovered podium height. The
baseline binary is the validated campaign-74 build; upstream source still has
the same single-match selection. No separate upstream-master binary was run.

For a manual client check, arrange overlapping crystals at a ritual position,
place the fourth-position crystal, and verify all eligible crystals beam toward
the center. Capture the start of the ritual with both overlapping beams visible.
