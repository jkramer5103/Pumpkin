# Wither skull origins during a movement turn

Assignment 52, lane jaron (Christine credentials only). Source baseline
`7824284eda2bd0a9494831294da8c5b7369a323d`. Validated against vanilla 26.3 in the bounded arena.

Vanilla 26.3 `WitherBoss.aiStep` turns entity yaw from horizontal velocity before
calling the server AI. Its `getHeadX`/`getHeadZ` use `yBodyRot`, which is updated
later by `LivingEntity.tick` -> `Mob.tickHeadTurn`. Pumpkin used entity yaw in
both helpers. A first-tick sideways movement therefore placed retaliation skulls
on the Z axis instead of the body's X axis. The correction reads `body_yaw` in
those two helpers. Main-head coordinates, scale, height, firing-slot indices,
projectile velocity and shared body-rotation control are unchanged.

The isolated arena primes six hurt attempts while ticks are frozen, sets a
horizontal velocity, then advances one tick. Both side heads fire dangerous
retaliation skulls. Vanilla launches them at `(13.7,82.2,15)` and
`(16.3,82.2,15)` even when entity yaw becomes +/-90 degrees. Baseline Pumpkin
instead launches sideways cases around `(15,82.2,13.7)` and `(15,82.2,16.3)`.
Forward and stationary cases are controls. Each case is repeated twice.

Run `lab/examples/wither-skull-body-rotation.json` using the existing controlled
tick arena tools with a creative observer. The fixture checks both skull
positions through selectors with a 0.001-block tolerance. The companion
`tests/check_wither_body_rotation.py` verifies the captured arena report:

```
python3 tools/parity-lab/tests/check_wither_body_rotation.py REPORT.json
python3 tools/parity-lab/tests/check_wither_body_rotation.py BASELINE.json --baseline
```

The local probe, build report and source/vanilla hashes are under
`/root/pumpkin-parity-lab/artifacts/jaron-wither52-*`. Initial exploratory runs
are excluded from final totals: baseline's initial tracking capture sometimes
contains only one skull packet, so an exact-two packet assertion was unsuitable.
An initial final report also had two preparation fills rejected before corner
chunks loaded; it is excluded from final totals. The final rerun waits for the
arena corner to load before executing any fixture rows. It uses authoritative
selectors for both skulls and checks captured initial skull origins separately.

The final identical fixture produced:

| Target | Checks passed | Expected origin failures | Controlled ticks |
| --- | ---: | ---: | ---: |
| Vanilla 26.3 | 64/64 | 0 | 233 |
| Baseline Pumpkin | 52/64 | 12 | 233 |
| Patched Pumpkin | 64/64 | 0 | 233 |

All eight rows on each target have two authoritative skulls. Vanilla captured 16
initial skull packets; baseline and patched Pumpkin captured eight. No claim is
made that both skulls' initial spawn packets were delivered. Both authoritative
position selectors and every captured launch origin agree after the correction.
Commands and fixture hashes match across targets. Source and copied binary hashes
match the completed Rust build report. Cleanup, process stops, Pumpkin save/stop
markers and server/client logs passed. Vanilla final-save completion was not
independently asserted.

All 444 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed under the shared build lock and resource
limits. The build reports a pre-existing future-compatibility warning in
`proc-macro-error2`; no new Clippy warnings were added. World-dependent regression
coverage is the live arena fixture; no isolated getter unit test was added.

Open upstream PRs were screened. PR4092 changes shared AI/body execution but does
not correct these head helpers. PR3835 handles projectile flight/damage context;
PR4107 handles targeting. Those broader changes were not included. Fork master
is already an ancestor of this campaign branch; no integration commit is needed.

Limitations: command-controlled velocity and first-tick retaliation, headless
protocol observation, default scale and initial body yaw zero. No rendered-client
visual, natural uncommanded flight, full-fight or whole-boss parity proof. A real
client can inspect skull emergence while a Wither turns, but visual verification
has not been performed. Broader body-control parity remains deferred to PR4092.
