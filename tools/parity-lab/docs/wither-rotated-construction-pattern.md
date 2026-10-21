# Wither construction rotations

Pumpkin recognized only upright soul-block T shapes. Official Java 26.3 also
summons the boss from inverted, flat and sideways structures. Dispensers must
recognize the same rotated base even before the skull row is complete.

The Wither-specific matcher now searches the 3×3×3 positive origin region in
X/Y/Z order, then the perpendicular forwards/up pairs in direction declaration
order. It preserves the nine-cell column order, matched base spawn position,
forwards-axis yaw, soul-block tag, skull/wall-skull predicate and required air
cells. State reads are cached during each bounded search. No shared block,
combat, entity tracker or navigation implementation is changed.

Official reference: `WitherSkullBlock.checkSpawn`, `canSpawnMob`, the full/base
pattern builders, `BlockPattern.find`, `matches`, `translateAndRotate`, and
`CarvedPumpkinBlock` clearing/update calls in the pinned official 26.3 server.
The local reference jar SHA-256 is
`a362163eec5d1612d520772bc16e5b39c09e3b234fdc045f56bf544284ee8ae6`.
The parity tracker and mob AI issue #3468 were used as leads; this campaign
already fixed the spawn-window goals. Current upstream still has the upright
matcher; the open Wither/BlockPattern PR searches showed no matching fix.
Fork master is already an ancestor of this branch.

## Regression and validation

The Rust test uses seven explicit coordinate layouts, each completed from all
three skull positions. It covers both upright axes, inverted, flat in both
directions, sideways in both directions, mixed soul sand/soil, wall skulls,
missing skulls, dispenser wildcards, missing soul blocks and obstructed air cells.
The expected layouts do not use the production rotation formula.

The live fixture has two trials of upright, inverted, flat and two sideways
constructions, plus obstructed-air, incomplete-base and incomplete-skull controls.
A real dispenser places the final skull while an exact 26.3/protocol 777 headless
client observes the isolated loopback arena. It checks boss existence, spawn
window, consumed blocks, inventory, initial spawn position/yaw and the nine
ordered destruction events. The checker compares vanilla and patched event
sequences and rejects the actual pre-fix result.

All validation passed under the shared Cargo lock, one job, disabled debug info
and incremental compilation, in a 5 GiB / zero swap / 200% CPU scope:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 447 passed
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

Vanilla and patched Pumpkin each passed 212/212 checks. Campaign 68 baseline
passed 152/212: 56 failures for the four rotated positive layouts across two
trials, and four failures for skull placement/item consumption on the incomplete
flat skull row. Upright and invalid-base controls passed. Gameplay command hashes
matched for all three targets; all 16 cases advanced 496 verified arena ticks per
target, followed by cleanup. Patched initial spawn position/yaw and ordered
construction destruction positions/state IDs matched vanilla. Source, copied
binary and fixture hashes matched. Cleanup and stopped-process checks passed;
server/client logs had no ERROR, panic or uncaught thread exception lines.

The copied patched binary SHA-256 is
`e83fd31bc8a1dbae7b3a692cc13a1e07eb491f97b5b101ad96013c28fa79f899`.
An initial generated-tag namespace compile error was corrected before successful
validation. Early command-property and observer-chunk setup attempts are retained
outside Git and excluded from final evidence. The existing `proc-macro-error2`
future-compatibility warning remains.

Local durable evidence: `artifacts/jaron-wither69-{verify,validation}.json`,
`artifacts/jaron-wither69-{vanilla,baseline,fixed}.log`,
`artifacts/jaron-wither69-source-provenance.json` and
`artifacts/jaron-wither69-upstream-overlap.json`. Jars, decompiled references,
worlds, logs and investigation clients remain outside Git.

This is bounded server-state and decoded-packet evidence, without rendered-client,
audible, Bedrock or whole-fight proof. The live baseline is campaign 68 rather
than a separately compiled upstream master; current upstream's missing rotated
matcher was checked directly. No claim of campaign completion follows.

## Dеscription ·

> This description was drafted by an AI agent (Codex, gpt-6.1-sol).

Recognize rotated Wither construction patterns, including dispenser base checks,
and preserve vanilla's matched base position, rotation and destruction order.

## Tеsting ·

All four Rust checks above passed. The isolated vanilla/baseline/patched comparison
passed 212/212, 152/212 and 212/212 respectively; no rendered client proof.

Human play-test checklist: build a sideways or flat soul-block T, place two
Wither skulls, then dispense the third. Expect one charging Wither at the base
cell and the construction to disappear. Block one required air cell and repeat;
expect no skull placement or boss spawn. Use an isolated test world.

Capture: <attach a real-client recording of the construction and charging boss here>
