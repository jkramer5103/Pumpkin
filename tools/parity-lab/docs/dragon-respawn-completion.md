# Dragon respawn completion releases the fight lock

The final dragon respawn tick could stop Pumpkin's world simulation. It created
the new dragon and reset the pillar crystals, then exploded the portal crystals
while holding the fight mutex. Explosion damage calls the crystal's damage
handler, which tries to acquire that same mutex to notify the fight manager.

The stage handler now returns the participating entities for consumption. The
outer tick releases the fight lock before clearing their beams, exploding them
and removing them. It retains owned references to every participant throughout
the explosions, including participants another explosion may already remove.
Dragon creation and pillar reset still precede those effects, following official
26.3 `DragonRespawnStage.SUMMONING_DRAGON.tick`.

The isolated reference ritual uses a headless Java client and a real fourth
crystal item placement. Initial crystals are removed to isolate completion from
pillar explosions. Official 26.3 completes all 620 requested ritual ticks, removes
the four portal crystals, leaves ten pillar crystals and creates one dragon.
Campaign84 completes 600 requested ticks, then stops progressing during the last
20-tick step until the deterministic tick controller times out. The scratch
process is stopped after that expected failure.

The focused regression fixture and checker are under
`fixtures/dragon-respawn-completion/` and
`tests/check_dragon_respawn_completion.py`. Additional final checks cover
damage acceptance on all ten pillar crystals, a healthy dragon,
continued ticking and dragon tracking packets. Patched Pumpkin and official
26.3 pass those checks: four initial ritual crystals become fourteen crystals
before completion, then ten pillar crystals remain alongside one healthy dragon.
All ten accept damage after the ritual, and the world advances another 40 ticks.
The successful runs have live headless observers, actual crystal item-use packets,
successful cleanup, stopped processes and no error or panic lines in their logs.
All 130 ritual stimulus commands through the final requested step are identical
on baseline and patched Pumpkin, excluding clock polling and earlier chunk setup.

One final trial per target supports these results. An earlier vanilla run without
the post-completion damage checks is exploratory evidence only. The baseline
report remains incomplete because it times out at the observed stall and requires
forced process termination. Crystal beam NBT queries through `execute as` produce
empty reference output and are not treated as proof that beams were cleared.
The ritual is sampled every 20 ticks; exact single-tick completion timing is not
asserted.

All 495 core Rust library tests, workspace formatting, core Clippy with all
targets/features and the debug server build pass under the shared Cargo lock and
resource caps. The existing `proc-macro-error2` future-compatibility warning
remains. Source and immutable binary hashes match the Rust validation record;
probe, fixture, checker, reports, packet traces and server/client logs are hashed
in `artifacts/christine-dragon85-live-validation.json`.

Fork master was already an ancestor of this branch. Read-only upstream review on
2026-10-23 found the same completion path and no overlapping correction in the
open dragon/crystal/respawn PRs. Multipart, healing and general crystal combat
changes remain deferred to their existing upstream work. The reproduced baseline
is campaign84; no separate upstream-master binary was built.

Evidence lives outside Git in `artifacts/christine-dragon85-*`. This is bounded
server-state and headless protocol evidence, without rendered-client, Bedrock,
reload, arbitrary layouts or whole-fight proof. In particular, the pillar-stage
explosion still runs inside the fight lock; interactions with surviving original
crystals there need a separate reproduction. General explosion source exclusion
and crystal combat parity are outside this correction.
