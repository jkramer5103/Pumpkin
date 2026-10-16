# Wither main-head ranged attack goal

Source fix: `062484426c310e2747494bc9900553ab6f83c96c`.

A Wither acquired a visible sheep 24 blocks away but never fired its main head. Pumpkin's manual timer incorrectly treated the ranged goal's 20-block navigation radius as a hard firing limit. Source review also found immediate firing on acquisition, a 41-tick repeat interval and no sight check in that loop.

The boss now implements `RangedAttackMob` and registers the existing `RangedAttackGoal` at priority 2 with speed 1.0, interval 40 and radius 20.0, matching official Minecraft Java 26.3 `WitherBoss.registerGoals`. The duplicate timer is removed. The existing projectile helper retains eye-height aiming, the 0.001 dangerous-skull chance and firing effects. Main-target metadata and side-head AI remain in the boss. The priority-zero spawn goal excludes the ranged goal by its movement/look controls.

Vanilla's `RangedAttackGoal.tick` delays the first shot, advances its timer every active tick, checks sight on firing and resets the interval to 40 ticks. Its radius controls navigation, allowing sighted shots beyond 20 blocks. Pumpkin already implements this goal; the patch wires the Wither into it without changing shared AI code.

Validation passed:

- Workspace formatting, all 443 `pumpkin-core` library tests, core clippy with all targets/features, and a full `pumpkin` build. All Cargo operations used the shared lock, one job, disabled debug info/incremental compilation, and the required 5 GiB memory/200% CPU scope. An interrupted clippy attempt was preserved; the remaining checks completed through a persistent systemd driver. The existing `proc-macro-error2` future-compatibility warning remains.
- Two repetitions of the same regression fixture: vanilla 40/40 checks, patched Pumpkin 40/40, baseline 32/40. Baseline fails only three visible-fire observations and the shot-count assertion per repetition.
- Each repetition advances exactly 172 arena ticks, holding the boss 24 blocks from a Resistance-protected sheep. It checks no shot through tick 40, firing by tick 44, the next firing interval, suppression behind bedrock and recovery after removal. Main-head metadata acquires the sole eligible sheep; side heads stay idle. Exactly three skull spawn packets prevent an unnoticed shot into the wall from passing the cover test.
- Identical fixture and gameplay-command hashes across all six trials, binary/source hashes, healthy bosses/targets, connected headless protocol 777 clients, cleanup, normal scratch-server shutdown logs and no server ERROR/panic lines.

Fixture: `tools/parity-lab/lab/examples/wither-main-head-ranged-goal.json`. Raw reports are `artifacts/jaron-wither20-final-{baseline,vanilla,fixed}-*/report.json`; detailed assertions/provenance are in `artifacts/jaron-wither20-validation.json` and Rust results in `artifacts/jaron-wither20-verify.json`. Fixture SHA-256: `bb3dfe49bec324041442640549ab8a13173290130b5aa8beca3d9cdb3280db5c`. Gameplay-command SHA-256: `d848c1330c2b1a3b1d63d3d569267b6ef16422665a9669dd1c8e404cea4f9e74`.

Observer corrections are recorded separately from preserved raw reports. The stationary Pumpkin client misses the distant sheep spawn packet, so a nonzero main target is checked against the fixture's sole eligible healthy sheep; when its packet is available, IDs must match. Vanilla omits unchanged side-head metadata whose defined default is zero; captured metadata must contain no nonzero side target. Read-only clock-poll counts vary, so gameplay hashes omit only `time query gametime`; all other commands and their order match. Tick barriers still verify every advance.

Overlap checked again before publication: fork master `65bca3f` is already an ancestor; upstream `b57d821` retains the manual timer. Open PR 4092 moves the same timer into a helper without registering the ranged goal. PR 3835 concerns projectile flight/attribution, PR 3905 wind-charge bursts and PR 3865 death/star drops. None supplies this correction. Issue 3468's ranged-goal entry was confirmed against source and gameplay.

Limits: this is headless server-state evidence, without rendered-client or whole-fight proof. First-shot assertions accept ticks 41–44 rather than one exact selector startup tick. Navigation/flight parity, target replacement/loss, spawn interruption, projectile flight, damage attribution, damage amounts and immunities are not separately validated here. Shared ranged-goal continuation behavior is unchanged. The excluded initial wind-charge/arrow investigation produced no source changes.
