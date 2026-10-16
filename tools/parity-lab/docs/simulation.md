# Simulation-dependent block behavior

This campaign adds one opt-in deterministic fluid scenario rather than expanding
the immediate-state count. It uses the engine's verified game-time barriers;
no assertion infers simulated ticks from a sleep.

Run against the permanent RCON targets:

```sh
python3 infra/validate_simulation.py --repeat 2
```

For a current-source binary without RCON, use a capped scratch console:

```sh
systemd-run --scope --unit=pumpkin-parity-simulation-check \
  -p MemoryMax=3G -p MemorySwapMax=0 -p CPUQuota=150% \
  python3 infra/validate_simulation.py --repeat 2 \
  --pumpkin-console /absolute/path/to/pumpkin
```

The wrapper takes the existing shared engine lock through `lab.runner.run`,
enables the private one-chunk source fixture, probes tick capability on both
engines, limits each case to 40 requested ticks, and retains the engine's raw
transcripts, scenario snapshots, errors, and exit status. A fixture load or tick
capability failure is visible. These results do not claim current-source RCON.

## Oracle and initial evidence

`scheduled-water-down` places a source at (2,65,2) over air above a solid floor.
It observes the source/air initial state, air after four verified ticks, downward
water on tick five, and persistent water on tick six. Every observation resets
`#probe pp_sim` to zero, conditionally sets one, then positively checks the score.
Only material is observed; exact water level and client rendering are untested.

On vanilla 26.3 and clean upstream master
`5b53f064af8708ba33fcaa533b81ca29a53a3310`, both tick probes verified one tick.
Two full six-tick trials then showed vanilla passing all four controls and
upstream passing the first, second and fourth controls but failing tick five.
The engine reported one repeatable difference, no infrastructure errors, and
supported timing. Raw baseline evidence:
`artifacts/jaron-simulation-final-draft-run/20261016T015107.432633Z-5e265326/`.
Drafts and failed probes remain in artifacts; they are not passing catalog cases.

Vanilla's decompiled `LevelAccessor.createTick` schedules at game time plus the
delay. `ServerLevel.tick` increments time before collecting due block/fluid ticks;
`LevelTicks` accepts trigger times less than or equal to that current time.
Pumpkin's scheduler drained the old cursor before advancing, adding one step to
positive delays. New scheduler regressions fail on the original code, including
save/reload, ring wrap, and rescheduling after a callback.

Open upstream PR 4010 addresses long delays and saved/generated tick tracking.
Its inspected scheduler diff and regression explicitly preserve `delay + 1`, so
it does not resolve this boundary defect. This campaign does not integrate that
PR or claim long-delay support. Open PR 3639 concerns inactive chunk gating;
forced-chunk work in PR 3845 is separate. Evidence and attribution are retained
in `artifacts/jaron-simulation-overlap-4010*.json` and the overlap search record.

## Blocked checks

| Behavior | Actual evidence | Remaining prerequisite |
| --- | --- | --- |
| Falling sand landing | Vanilla passed the initial block, falling entity after tick two, and settled block after 22 total ticks twice. Source console chunk became unloaded during the longer run. | Sustained loaded and ticking chunk; supported observation commands. No passing Pumpkin physics claim. |
| Redstone lamp shutoff | The corrected vanilla fixture places the lamp before power. Initial lit state, lit after three ticks, and off after four passed twice (`artifacts/jaron-simulation-lamp-vanilla.json`). The failed initial draft is preserved. | Source property syntax is unsupported; a supported lit-state oracle is needed before promotion. No Pumpkin lamp timing pass. |
| Random growth | Not attempted; the lab disables random ticks for reproducibility. | A controlled random source/selection or deterministic growth trigger on both engines. Advancing a fixed number of ticks alone cannot guarantee growth. |
| Full fluid levels, redstone networks, client physics | Not attempted. | Working property observations and, where needed, actual connected clients. |

The schema has no prerequisite metadata field. Blocked checks remain documented;
see [the engine integration note](simulation-integration.md). No tests were
removed or loosened to turn these gaps into passes.

The released RCON candidate was also tested twice with the final scenario. Both
engines verified six tick advances, but the release rejected the observation
commands and reported unloaded-world errors. The engine exited 2 with one
infrastructure-error scenario; this is not a source defect count or a physics
pass. Vanilla passed all four observations in both trials. Evidence:
`artifacts/jaron-simulation-release/20261016T015514.235671Z-103286eb/`.

Python validation: 22 assigned scenario/infrastructure tests and all 105 lab
unit tests passed. The added oracle test uses an independent fluid fixture with
correct tick-five and late tick-six schedules: the former passes, the latter
produces a confirmed repeated difference with only the tick-five control failing.

The final scenario also reproduced the tick-five defect through the new launcher twice on clean upstream, with no infrastructure errors: `artifacts/jaron-simulation-upstream/20261016T015605.489773Z-4cfb8915/`. The patched-source build and world-crate validation are still running; no fixed live pass is claimed yet.
