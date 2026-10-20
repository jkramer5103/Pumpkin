# Wither idle flight with passengers

Assignment 62 fixes the Wither's idle flying goal treating every passenger as a
controller. A creative player or armor stand mounted with `/ride` prevented the
boss from strolling in Pumpkin, while vanilla continued to choose idle routes.
An inert zombie passenger is a controller even with its own AI disabled and must
continue to suppress the Wither's own stroll goal.

Vanilla 26.3 `RandomStrollGoal.canUse/canContinueToUse` calls
`hasControllingPassenger`. `Mob.getControllingPassenger` considers only the first
passenger, requires a Mob and enabled vehicle AI, and applies
`Entity.canControlVehicle` (the `non_controlling_rider` entity type tag).
The Wither does not override this method. Pumpkin's flying goal instead checked
`has_passengers` at both boundaries. The correction applies the vanilla predicate
at both boundaries, using the existing generated tag. Only the Wither currently
installs this goal; other stroll goals and shared rider movement are unchanged.

Fork master 65bca3f7 is already an ancestor. Upstream master fb7c8e223 still has
both broad passenger checks. Open PR4092 adds a shared controller API and
navigation foundation but leaves these flying-goal checks unchanged; the private
goal predicate avoids changing that shared layer. Issue3468 and the tracker were
reviewed as leads. Prior invulnerability, target, damage, construction and route
patches were inspected and are outside this correction.

The same eight-case fixture passed118/118 checks on vanilla and118/118 on the
patched binary. Prepatch Pumpkin passed114/118, failing exactly both player and
both armor-stand idle-flight checks. Each failing case stayed at0 horizontal
displacement for1200 controlled ticks. Patched player/armor-stand cases moved
1.03–2.10 blocks. All zombie controls stayed at0, and all empty controls flew.
Runs used2126/5766/2686 controlled ticks respectively, including preparation and
cleanup. Riding relations, presence, AI, bounds, target metadata, source/fixture/
binary hashes, cleanup and clean server/client logs passed.

Rust validation passed: 444 core library tests, workspace formatting, core
all-target/all-feature Clippy and debug server build, serialized with the shared
build lock and 5GiB/zero-swap/200%CPU limits. An existing proc-macro-error2
future-compatibility notice remains. The world fixture and report checker provide
the new regression coverage; no new mocked Rust unit test was added.

Raw evidence is outside the repository:

- `artifacts/jaron-wither62-validation.json`, `verify.json`, `source-provenance.json`
  and `prepush-overlap.json` (with the common `jaron-wither62-` prefix).
- Vanilla: `jaron-wither62-live-vanilla-20261020T164733.651136Z/report.json`.
- Prepatch: `jaron-wither62-live-baseline-20261020T165017.560626Z/report.json`.
- Patched: `jaron-wither62-live-fixed-20261020T165521.236106Z/report.json`.
- Fixture SHA256: `a53fd3f260e8bcf6c005ca6596c38f4faf7ecb98c193dce5073271f9bddeec26`.
- Patched binary SHA256: `52c43d29b2b6122d8d7b7e0573f0511723e548fd0c20f9079457075b6f33580f`.

The fixture uses an enclosed bedrock arena and an actual headless protocol777
client. The world checker requires the riding relation, boss presence/bounds,
enabled AI, no invulnerability, no attack targets or other mobs, controlled ticks,
cleanup, server shutdown and clean client/server logs. Player passengers are not
included in saved Passengers NBT; the command relation check establishes riding.
Random destinations and delay differ between servers. This does not establish
whole-fight, ordinary survival, Bedrock or rendered-client parity. The tagged
non-controlling Mob passenger branch is source-checked but not exercised by this
player/armor-stand/zombie fixture.

For rendered-client verification, mount a creative player or armor stand on a
Wither in a safe enclosed test world and observe that idle flight continues;
compare with a NoAI zombie rider, for which the Wither's own idle flight stops.
No recording or human-client proof is claimed.
