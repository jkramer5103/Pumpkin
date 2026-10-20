# Dragon strafe target height

After completing its strafe approach, the dragon aims slightly below a nearby
player's feet. Pumpkin clamped the height offset at zero, so a dragon level with
its target stayed level instead of beginning that descent. The phase now applies
only the upper cap and widens the original float constant before the calculation.
Only the strafe phase's target-height calculation changes.

Vanilla reference: Minecraft Java 26.3 `DragonStrafePlayerPhase.doServerTick`.
After `currentPath.isDone()`, it computes the horizontal distance and caps
`0.4F + distance / 80 - 1` at 10. The negative offset is intentional. The caller
then steers and moves the dragon before damping its vertical velocity.
`setTarget` uses the same height expression for its terminal approach node;
Pumpkin's separate approach-path initialization remains outside this patch.

Discovery used an isolated arena with a connected headless protocol 777 client.
A survival player at (8,120,0) was acquired by a circling dragon. Preparation
advanced the existing path, and the controlled samples reset the dragon to
(8,120,z), yaw 180, with zero velocity before one simulation tick. Facing away
prevents an attack from ending the phase. Vanilla descended at distances 20, 30
and 40; baseline Pumpkin stayed level. At distance 60, both ascended.

The focused regression fixture stores vanilla's observed position and velocity,
not an independent copy of the implementation formula. Two trials each repeat
all four distances and include a NoAI control. The checker verifies actual tick
advances, target acquisition, completed approach, phase, player presence and
health, positions, initial velocity/yaw, clear space, horizontal flight, cleanup
and identical controlled commands. Adaptive acquisition/preparation is excluded
from the controlled-command hash. Read-only clock poll counts also vary with
response timing and are excluded; each actual one-tick advance is verified.

The regression fixture is `fixtures/dragon-strafe-target-height/cases.json`;
`tests/check_dragon_strafe_target_height.py` checks the raw arena report.

Rust validation passed: 490 `pumpkin-core` library tests, workspace formatting,
core all-target/all-feature Clippy and the debug server build. Every Cargo
operation used the shared lock, one job, disabled debug information/incremental
compilation and the 5 GiB/zero-swap/200% CPU limits. Initial Clippy rejected a
separated literal suffix; changing its spelling preserved the value and type.
Formatting and Clippy were rerun after that correction. The existing
`proc-macro-error2` future-compatibility notice remains.

The first final arena attempt is excluded from acceptance because a preparatory
air fill crossed an unloaded endpoint chunk on both Pumpkin targets. Its sampled
positions were clear and its flight responses matched, but the repeat narrows the
fill to loaded chunks. The checker also accepts vanilla's equivalent -180 yaw
representation for the commanded 180. Neither adjustment changes the Rust patch,
reference fixture values or controlled movement commands.

The final arena passed 18/18 samples on vanilla and patched Pumpkin. Baseline
passed 6/18, failing exactly the 12 close-range descent samples. The remaining
four positive-offset samples and two NoAI controls passed on every target.
Each target received 18 controlled simulation ticks; all controlled commands
match after excluding read-only clock polls. Source, copied-binary and fixture
hashes match the validation records. All scratch processes stopped, and the six
server/client logs contained no ERROR/panic lines. All setup and sampling controls
passed, including the narrowed air fill.

| Horizontal distance | Vanilla / patched one-tick height change | Baseline |
| --- | --- | --- |
| 20 | -0.000175 | 0 |
| 30 | -0.000075 | 0 |
| 40 | -0.000025 | 0 |
| 60 | +0.000025 | +0.000025 |

The checker was re-run on the preserved final report after excluding variable
read-only clock polling from the command hash. No source, binary, fixture values
or simulation steps changed for that correction.

Final raw report:
`artifacts/christine-dragon62-height-live-20261020T215411.277474Z/report.json`.
Checked evidence: `artifacts/christine-dragon62-live-validation.json`.
Retained local discovery evidence:
`artifacts/christine-dragon62-height-live-20261020T214223.674111Z/report.json`.
Rust checks: `artifacts/christine-dragon62-rust-validation.json`.

The [tracker](https://pumpkinmc.org/tracker/) and
[mob AI issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) were reviewed as
leads. Fresh authenticated searches for open dragon/strafe/strafing PRs and
public diffs for #3407/#3661/#3835/#4080/#4092 found no overlapping correction.
Fork master was fetched and is already an ancestor of the campaign branch; the
relevant prior dragon fixes are retained. No upstream implementation was copied.

The live baseline is campaign commit `b3971a6ae`, not a separate upstream-master
binary. The fetched upstream source retains the same lower clamp; this phase's
prior campaign corrections are present in both baseline and patched builds.

This is headless server-state evidence, not rendered-client or whole-fight proof.
Existing strafe routing/path initialization, traveling fireballs, multipart
hitboxes, crystals and the rest of the fight remain separate work. In a human
play check, observe a dragon with a completed strafe approach at the same height
as a nearby player: it should begin descending slightly below the player's feet
while continuing its approach. The small per-tick change is measured numerically
by this fixture and is not claimed as visually confirmed.
