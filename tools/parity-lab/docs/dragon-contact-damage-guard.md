# Ender Dragon contact damage after a recent living-attacker hit

Vanilla 26.3 `EnderDragon.knockBack` pushes an eligible wing-contact victim,
but only attempts its five-point attack when the victim's last living-attacker
hit is more than two entity ticks old. This covers other living attackers and
players. Pumpkin previously attempted damage on every eligible contact tick.

The correction adds that damage-only gate. Living hit memory tracks accepted
living-attacker hits independently of health loss, excluding `no_anger` damage
and the vanilla wind-charge victim exemption. Its entity-tick interval, reference
expiry/death handling, respawn initialization and NBT fields follow vanilla
`LivingEntity.resolveMobResponsibleForDamage`, `baseTick`, `setLastHurtByMob`
and additional save/load methods. Existing kill-credit fields remain separate.

Fork master `65bca3f` is already an ancestor; upstream master `5b53f06` has no
guard. Open PRs 3407/3661 cover parts, incoming damage, crystals and fight state;
PR 4080 covers team damage; PRs 3793/3794 cover touch/velocity. Inspected patches
do not implement this interval. Leads:
[Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[parity tracker](https://pumpkinmc.org/tracker/). The tracking issue describes
recent dragon damage, but the vanilla source checks any living attacker.

All 456 pumpkin-core library tests, workspace formatting, core all-targets and
all-features clippy, and the full Pumpkin binary build pass. Cargo used the
shared lock, one job, disabled debug info/incremental, MemoryMax=5G,
MemorySwapMax=0 and CPUQuota=200%. The new guard boundary regression fails when
the gate is replaced with the old unconditional behavior. The existing
proc-macro-error2 future-compatibility warning remains.

Source commit: `22f1ac9`. The source-file hashes and recorded build-parent plus
Rust diff match that commit. Immutable binary SHA-256:
`8f70939f3012c8dc7401b15452d34297efae7e2fae78f3db3c37d6ab3fed2f8b`.

The isolated arena comparison uses one dragon per sample, mob griefing and
natural health regeneration disabled, a protocol-777 headless player, and
frozen/stepped ticks. Functions batch a preceding one-point hit, direct health
read and contact step to avoid timing gaps between manual commands. Two trials
of six cases yield these post-contact health values, starting from 20 health:

| Preceding hit and contact duration | Vanilla | Baseline | Patched |
| --- | ---: | ---: | ---: |
| Cow-attributed hit, one tick | 19 | 15 | 19 |
| Cow-attributed hit, two ticks | 19 | 15 | 19 |
| Cow-attributed hit, three ticks | 15 | 15 | 15 |
| Unattributed generic hit, one tick | 15 | 15 | 15 |
| Cow-attributed no-anger hit, one tick | 15 | 15 | 15 |
| No preceding hit, one tick | 15 | 15 | 15 |

Vanilla and patched each match all 12 expected guard decisions; baseline matches
8 and reproduces four mismatches. Push remains measurable in all 36 accepted
samples, including suppressed-damage cases. All samples have exact initial
player/dragon positions, requested clock deltas, healthy starting state,
confirmed previous-dragon removal and matching command/function hashes.
Pumpkin functions directly confirm the preceding hit leaves 19 health. Vanilla
RCON suppresses internal function feedback; an earlier scoreboard reference
independently confirms all ten preceding hits leave 19 and both no-hit controls
start at 20.

The main run's last no-hit control on each Pumpkin target lost its player when
the headless client's 4,096-event cap was exceeded. Those two attempts are
invalid and retained, not counted as passes. Separate short reruns of only those
controls pass and supply the second no-hit sample. All five final scratch
servers stopped cleanly with no server ERROR or panic lines. Earlier manual
fixtures with timing/regeneration confounds and execute-store diagnostics
rejected by Pumpkin are retained separately and excluded from final proof.

Original fixtures: `tools/parity-lab/fixtures/dragon-contact-guard`. Enable the
copied pack in a private 26.3 world, reload it, set function-permission-level=4,
and connect the offline player ParitySmoke. Freeze time; disable mob griefing,
spawn_mobs and natural_health_regeneration; force-load x/z 0..15 and place a
floor at y=79. Spawn one invulnerable NoAI cow at (28,80,28) and an airborne
phase-0 dragon at (8,80,8). Settle for two ticks, teleport the dragon back with
yaw 0, and stage a healthy creative ParitySmoke at (12,80,8), yaw 0. Run one
fixture function. Each sample needs a fresh dragon and sufficient stepped
cleanup time to remove the previous dragon. The task driver used 210 ticks.

Local evidence: `artifacts/christine-dragon13-final-rust-validation.json`,
`christine-dragon13-source-provenance.json` and
`christine-dragon13-live-validation.json`. Final raw reports are the
`christine-dragon13-live-20261016T170944.877057Z` three-target run and the
`171937.553669Z` / `172040.844600Z` control reruns. Logs, worlds and decompiled
source remain local.

Limits: the gate applies to the existing player contact query. Multipart
volumes, nonplayer contacts, perched contacts, team rules, other damage formulae
and complete fights remain separate work. NBT persistence, reference expiry,
attacker death and wind-charge exemptions have focused Rust coverage rather
than independent live lifecycle tests. Shield interactions and full resistance
cases were not exercised. Headless server-state evidence does not establish
client visuals, prediction or exact Motion parity.

Human play-test checklist: in an isolated arena, take a weak hit from another
living attacker immediately before entering an airborne dragon's wing. Expect
wing push during the short damage guard and contact damage after it expires.
Record the hit, push and health change from a real client before any upstream
submission. Capture: <attach screenshot or recording here>
