# Dragon respawn pillar blocks

Dragon respawn now rebuilds damaged obsidian columns and clears the feature's
upper volume before restoring the cap and crystal. Previously, regeneration
restored only the crystal, cap, fire and cage, leaving holes and replacement
blocks in the pillar body.

The official 26.3 `DragonRespawnStage.SUMMONING_PILLARS` calls
`EndSpikeFeature.place`, then `placeSpike`. That method rewrites the circular
column from the dimension minimum Y to one below the cap, including the squared
radius plus one boundary. Outside the column it clears blocks above Y=65 through
height+10 within the radius square. Blocks at Y=65 outside the circle and above
the top boundary remain untouched by the feature.

The focused fixture and `check_dragon_respawn_pillar_blocks.py` consume isolated
server reports. A headless protocol 777 player starts a real respawn ritual with
an end-crystal item after killing the initial fight dragon. Before the ritual,
two pillars receive holes, a stone replacement and obsidian boundary markers.
The checker verifies the setup blocks, twelve positions per pillar, regenerated
caps/crystals, exactly 185 observation ticks, a third-pillar hole remaining until
its own turn, cleanup and stopped scratch servers. Heights and radii are derived
from each world's actual cap, since pillar layouts differ between targets.

Validation passed:

- `cargo fmt --all -- --check`, 493 `pumpkin-core` library tests,
  `cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
  `cargo build --locked -p pumpkin` passed under the shared Cargo lock and
  required resource limits. Only the existing `proc-macro-error2`
  future-compatibility notice remains.
- Official 26.3 and the patched binary both produce all 24 expected sample
  blocks. Campaign 72 leaves exactly 18 incorrect samples; its six preservation
  controls pass. Both regenerated columns, including the inclusive circular
  edge, bottom, replacement block and upper clearing boundary, are covered.
- The identical probe and fixture pass actual item-use, regenerated cap/crystal,
  exact 185 observation ticks, untouched third-pillar, player/client, cleanup
  and stopped-process controls on all three targets. The contiguous protocol
  packet file identifies each regenerated crystal after the actual item-use.
- Source, copied binary, probe, fixture, checker, packet and log hashes are
  recorded in the live campaign artifacts. Six server/client logs contain only
  known startup warnings, with no errors. Baseline is the verified campaign 72
  binary; upstream was reviewed in source without a separate upstream build.

The focused live regression covers real world block updates; no additional mock
world or constructor-only Rust test was added. The 493 existing Rust tests support
the source change without proving a complete boss fight.

Upstream master `9c04f714bb7eb26579c652f9744895d465ee902b` retains the omitted
body regeneration. Read-only searches found no open spike/pillar PR. PRs 3694,
3407 and 3661 affect crystal combat, dragon parts or fight tracking, without
implementing pillar body regeneration. Fork master is an ancestor of the campaign
branch; all existing relevant campaign fixes are retained.

This bounded check does not prove a complete dragon fight, rendered-client
appearance, Bedrock, chunk reload, custom dimensions, all cage properties or full
respawn completion. The separate respawn destruction cube still preserves
obsidian/bedrock in Pumpkin, whereas vanilla removes those blocks before placing
the feature. That is a distinct candidate, outside this correction.
