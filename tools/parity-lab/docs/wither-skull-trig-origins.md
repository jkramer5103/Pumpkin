# Wither skull launch trigonometry

Assignment 64, lane jaron (Christine subscription only). Baseline
`58e66204d028b1ed3c10775a8517aa9784a5f47d`; reference vanilla Java 26.3.

Vanilla `WitherBoss.getHeadX/getHeadZ` computes a float angle from body yaw,
then calls `Mth.cos/sin`. Minecraft uses a 65,536-entry float sine table, indexed
with double multiplication and a masked integer cast. Pumpkin's existing
`pumpkin_util::math::{cos,sin}` implements this lookup, but the Wither called
Rust's standard float trigonometry instead. The correction uses those existing
helpers for skull launch offsets.

The difference affects real projectile positions, including at body yaw zero.
After six frozen-tick damage attempts, both side heads fire retaliation skulls
on the next tick. At scale 16 and boss position `(15,100,15)`, vanilla launches
at `(-5.800000000000001,135.20000076293945,15.000000000000002)` and
`(35.8,135.20000076293945,15)`. Prepatch Pumpkin instead uses Z coordinates
`14.999998181606248` and `15.000003636787506`. At default scale the differences
are approximately 0.000000114 and 0.000000227 blocks. These are small numerical
errors; no perceptible visual or whole-fight effect is asserted.

The regression fixture `fixtures/wither-skull-trig/cases.json` preserves actual
vanilla origins and the gameplay commands for scales 1, 4 and 16, repeated twice.
The checker verifies both skulls against a 1e-9-block tolerance, preserves the
unchanged X/Y controls, and checks scale-setting success, boss position/rotation,
observer presence, exact command sequences, controlled ticks and cleanup:

```sh
python3 tools/parity-lab/tests/check_wither_skull_trig.py VANILLA_REPORT.json
python3 tools/parity-lab/tests/check_wither_skull_trig.py BASELINE_REPORT.json --baseline
python3 tools/parity-lab/tests/check_wither_skull_trig.py PATCHED_REPORT.json
```

The identical vanilla and baseline stimuli each advance 182 controlled ticks.
Vanilla passes 60/60 checks. Baseline passes 48/60, failing exactly both origin
checks in every case. The discovery probe used an incorrect scale-response
prefix; the checker verifies the preserved raw success/value response instead.
Neither commands nor raw reports were changed. The incomplete initial run that
was stopped while waiting for the shared engine lock is excluded.

Workspace formatting, 446 core Rust library tests, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock, one build
job, disabled debug information/incremental compilation and 5 GiB/zero-swap/200%
CPU resource limits. The pre-existing proc-macro-error2 future-compatibility
notice remains. Patched Pumpkin passes 60/60 checks with the same 182 controlled
ticks and identical command hashes. Both side-head launch positions match vanilla
at all three scales in both trials. Source, copied binary and fixture hashes,
cleanup/process stops and clean server/client logs passed. Local source/binary hashes,
full reports, build commands and the Java oracle using the official server jar
are recorded in `/root/pumpkin-parity-lab/artifacts/jaron-wither64-*`.

Fork master was already an ancestor of this branch. Current upstream retains
standard trigonometry in these helpers. Open PRs 3835 (projectile flight/context)
and 4092 (AI/controller/bossbar foundation) do not change these coordinates;
PR4107's armor-stand targeting fix is separate and excluded. No shared math or
entity files change. The helpers feed `WitherEntity.perform_ranged_attack` for
side-head aimed and random shots; the main-head branch returns its base position.
Existing spawn events, projectile construction, scale and height calculations
continue through the same path.

Limitations: first-tick command-primed retaliation, body yaw zero, three scales,
headless protocol observer and authoritative server state. No rendered-client,
Bedrock, collision-outcome or natural-fight proof. Arbitrary body-yaw live
comparisons are masked by the body-controller foundation deferred to PR4092;
non-cardinal Java math observations are not counted as world validation. Focused
world regression coverage is used instead of a mocked getter unit test.
