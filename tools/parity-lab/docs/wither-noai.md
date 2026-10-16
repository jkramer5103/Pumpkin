# Wither custom AI and NoAI

A Wither with `NoAI:1b` still counted down its spawn invulnerability, healed and
fired side-head skulls in Pumpkin. Vanilla 26.3 freezes these custom AI effects.
For example, after 41 verified ticks, a Wither summoned with `Invul:220` and
`Health:100.0f` retained both values on vanilla. The pre-fix Pumpkin binary reached
`Invul:179` and 140 health, in both repetitions. An idle NoAI Wither also healed
from 200 to 202 health, while vanilla retained 200.

The Rust change routes `tick_wither` through `custom_server_ai_step`, which the
existing mob tick already gates on NoAI. Movement remains in `mob_tick`, mirroring
the separate vanilla `WitherBoss.aiStep` call, and reads the main head's synced
target. Peaceful removal remains outside the gate. No shared mob files change.
The existing death/drop implementation is not corrected by this patch.

Reference: vanilla 26.3 `Mob.isEffectiveAi` rejects NoAI before
`LivingEntity.aiStep` calls `serverAiStep`; `Mob.serverAiStep` calls
`WitherBoss.customServerAiStep`. That Wither method handles spawn countdown,
healing, boss-bar progress, head targeting/attacks and block destruction.
`WitherBoss.aiStep` separately damps velocity and pursues the main head target.
The decompiled source was inspected locally and is not included here.

The [mob AI tracker](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) was used
as a lead. Its missing invulnerability-window goal is a separate candidate,
not part of this patch. Open Wither PR 3865 concerns death/drop behavior; PR 3793
changes the Wither tick-count field but does not relocate this custom AI hook.
No matching open NoAI relocation was found in the overlap check.

## Focused regression fixtures

- `wither-spawn-noai.json`: countdown and healing remain frozen for 41 ticks;
  enabling AI for 10 ticks resumes both; disabling it again freezes both for
  another 20 ticks.
- `wither-spawn-ai-enabled.json`: exact countdown and healing positive control.
- `wither-noai-skulls.json`: a visible iron golem cannot provoke skulls from a
  NoAI Wither, and idle health remains unchanged for 41 ticks.
- Existing `wither-side-head-visible.json`: paired positive firing control.

Run these only in isolated scratch worlds, using frozen ticks and verified tick
steps. Keep Pumpkin's arena chunk loaded with a protocol client; a console-only
forceload request does not establish that condition. Use a fresh arena per case,
repeat twice, and require the initial/final wall and target controls to pass.
Fixtures observe actual server state and skull entities; they do not establish
rendering, human visual correctness, or whole-fight parity.

## Validation

The pre-fix current-source binary failed all three spawn-NoAI observations and
both disabled attack/regeneration observations in each repetition. Both enabled
controls passed. Raw scratch evidence is retained outside Git in the deployment
workspace, under `artifacts/jaron-wither-noai-fixtures-20261016T080307.290865Z/`.

Rust checks passed under the shared Cargo lock, one build job, disabled debug
info/incremental compilation, and the required 5 GiB / no-swap / two-CPU caps:
`cargo fmt --all -- --check`, all 443 `pumpkin-core --lib` tests,
`cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and
`cargo build --locked -p pumpkin`. Only the existing `proc-macro-error2`
future-incompatibility notice remains.

Vanilla passed two repetitions of the NoAI spawn, skull/health, and enabled
firing fixtures. The enabled spawn control now registers its disabled entity
for one tick before enabling AI for 40 ticks: a fresh vanilla chunk can delay
its first entity tick. The first attempt with an immediate-ticking assumption
failed and is retained as fixture evidence; the corrected control passed twice.
The patched replay passed all 30 gameplay observations and eight environment
guards across two repetitions of these four fixtures, matching vanilla's
hash-matched fixture results. Each replay used isolated scratch worlds and verified
tick barriers; all scratch processes stopped cleanly. The eight patched console
logs contain no ERROR/panic lines. The exact patched binary SHA-256 is
`e4226f29b2c7414cbb9a01a29b6baf887c13ce10a5ade8889d9f78b1ab46dc5d`.
Final raw results: `artifacts/jaron-wither-noai-fixtures-20261016T115417.000171Z/report.json`;
vanilla reference/control results: `artifacts/jaron-wither-noai-fixtures-20261016T114640.250344Z/`
and `artifacts/jaron-wither-noai-fixtures-20261016T114830.738066Z/`.
A completion assertion record checks the fixture hashes and baseline failures.

Boss movement, boss-bar appearance, block destruction during NoAI, and the full
spawn explosion/fight were not independently validated by these fixtures.
The regression coverage is executable gameplay fixtures; the 443 Rust unit tests
are supporting checks rather than a new unit-test claim.

For a human play check, use a disposable world: summon a NoAI Wither with a
positive Invul timer and low health beside a visible iron golem. Expect no timer
advance, healing, spawn explosion or skulls until AI is enabled. Enable AI and
observe the countdown/healing resume; disable it again and confirm they freeze.
Record that transition and the enabled attack control with a real client before
using this change in an upstream submission. No human client capture is claimed.
