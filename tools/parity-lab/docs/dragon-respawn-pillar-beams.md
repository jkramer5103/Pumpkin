# Regenerated dragon respawn pillar beams

When a dragon respawn ritual regenerates a pillar, its new crystal must beam
up to the ritual center immediately. Pumpkin's `regenerate_spike` initializes
its crystal without a beam target, so this part of the animation is absent.

The official 26.3 `DragonRespawnStage.SUMMONING_PILLARS.tick` passes `(0,128,0)`
to `EndSpikeFeature`; `placeSpike` sets the beam before adding the crystal.
The fix passes the fight's existing center target into `regenerate_spike`
and sets it before tracking begins. Ordinary crystals retain their defaults,
and the existing abort/completion reset clears regenerated crystal beams.

The focused world regression is
`fixtures/dragon-respawn-pillar-beams/cases.json`, checked by
`tests/check_dragon_respawn_pillar_beams.py`. It uses actual crystal item
placement to start an isolated End ritual, observes two regenerated crystals'
spawn metadata, checks an ordinary crystal, and aborts by breaking a portal
crystal. The private protocol client expands vanilla bundle packets to expose
both spawn and metadata packets. The checker requires each crystal's first transmitted beam target to be the
center and verifies a cleared target after abort. It reads the full packet
stream because asynchronous network callbacks can fall between tick snapshots.
The observer moves near both pillars after the four initial portal beams are
observed; a missing subject spawn packet fails the check.

Validation passed:

- 493 `pumpkin-core` Rust library tests, workspace formatting, core
  all-target/all-feature Clippy, and a debug server build, serialized under
  the shared Cargo lock and required resource limits.
- One identical-probe comparison against official 26.3, campaign 71, and the
  patched binary. Vanilla and patched Pumpkin transmit `(0,128,0)` for both
  regenerated crystals; the baseline transmits neither beam. Each target
  advances exactly 185 observation ticks before the abort controls.
- Ordinary crystals have no beam; all four initial portal beams are observed;
  abort clears both regenerated beams on vanilla/patched Pumpkin; the second
  pillar crystal retains its identity across abort and becomes destructible.
  Actual item-use, loaded player, cleanup and stopped-process controls pass.
- Source, committed source, fixture/checker/probe and binary hashes are recorded
  privately. All six final server/client logs contain only known startup
  warnings and no errors. The existing `proc-macro-error2` future-compatibility
  notice remains. Earlier client-classpath/range setup failures are excluded.

The focused regression is a world fixture; no isolated Rust unit test was added.
The protocol checker uses each crystal's first transmitted beam target, rather
than asserting the exact asynchronous packet-arrival tick.

Upstream review: fetched master `44d881c32` retains the missing initialization.
Open PRs [3694](https://github.com/Pumpkin-MC/Pumpkin/pull/3694),
[3407](https://github.com/Pumpkin-MC/Pumpkin/pull/3407), and
[3661](https://github.com/Pumpkin-MC/Pumpkin/pull/3661) cover crystal combat and
multipart lookup; their inspected diffs do not initialize regenerated beam
targets. Fork master and its existing campaign fixes are already ancestors of
this branch. No shared combat/entity files are changed.

Evidence is headless protocol/server state only. Rendered Java appearance,
Bedrock, successful ritual completion, reload, custom fight origins, full
pillar reconstruction, and a complete boss fight are outside this fixture.
The baseline is the prior campaign binary with the identical regeneration
method, rather than a separate upstream-master binary.

For a visual follow-up, join an isolated End with a real Java client, complete
the first fight, and place four crystals on the exit podium. Expect each
regenerated pillar crystal to beam toward the center; break a portal crystal
and expect those beams to disappear. Capture a recording of regeneration and
abort. No rendered-client capture was produced by this task.
