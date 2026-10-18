# Dragon flight turn speed

Pumpkin used a constant default turn speed of 0.1. A dragon at rest therefore
turned too slowly, while a fast dragon turned too quickly. The dying flight also
passed a separate hardcoded 0.1 into steering.

The default now depends on horizontal velocity, following vanilla 26.3
`AbstractDragonPhaseInstance.getTurnSpeed`. If `s` is the horizontal speed cast
to float plus one, turn speed is `0.7 / min(s, 40) / s`. Vertical velocity does
not affect it. Dying flight uses the same inherited phase method. Landing keeps
its existing override. Other default phase handlers receive the corrected rate
through the existing steering call; no shared entity or movement code changes.

The vanilla call chain inspected was `EnderDragon.aiStep`, the abstract phase
method, and the hover, landing, charge and dying phase implementations. Vanilla
queries the phase rate after changing vertical velocity and before adding flight
acceleration; Pumpkin reads horizontal velocity at the equivalent steering point.
Dying flight uses Pumpkin's existing separate steering site.

## Reproduction

The existing isolated server and protocol-client harness runs
`lab/examples/dragon-turn-speed.json`. A fresh hovering dragon establishes a
target, then receives a matched position and yaw plus a known horizontal motion.
One controlled tick produces these vanilla yaw changes:

| Motion X/Z | Yaw change |
| --- | --- |
| 0 / 0 | -3.5 degrees |
| 0.5 / 0 | -1.5555557 degrees |
| 1 / 0 | -0.875 degrees |
| 3 / 4 | -0.09722223 degrees |

Baseline Pumpkin produces -0.5 degrees in all four cases. Two trials also cover
NoAI suppression, the unchanged landing override, and dying flight at rest and
at speed one. An isolated bedrock podium at Y=79 keeps dying flight within
vanilla's 150-block target range. Summoned dragons run only in scratch Overworld
arenas; these checks do not exercise an End fight manager.

## Validation

The identical final fixture passed 44/44 checks on vanilla and patched Pumpkin,
and 32/44 on baseline.
The twelve baseline failures are exactly the hover/dying yaw assertions across
two trials. Each target advanced 26 controlled ticks, kept a connected protocol
client, and stopped. No server error/panic lines were logged; both Pumpkin saves
completed. Vanilla's final save marker was not observed within the shutdown grace.
The exploratory dying run without the raised podium is excluded.

Both focused regressions failed when the old constant was restored. All 479
pumpkin-core library tests, workspace formatting, core all-targets/all-features
Clippy and the debug server build passed under the shared Cargo lock with one
build job, disabled debug/incremental data, MemoryMax=5G, no swap and CPUQuota=200%.
The copied binary and final Rust source hashes match the verification record.
Matched fixture and stimulus hashes, connected client presence, copied binary
hash and final Rust source hashes were verified across the comparison.

The two Rust regressions cover observed vanilla turns, vertical/sign invariance,
and the one-factor speed cap. Extreme speeds at the cap are source-level coverage,
not live observations: vanilla clamps oversized Motion components on NBT loading.

## Limits and overlap

This is headless server-state evidence, with a connected protocol client. No
rendered client, complete dragon fight, natural charge trajectory, general movement
ordering, yaw wrap, collision flight termination, or dying target-height proof is
claimed. The fixture resets position and motion to isolate turn rate.
Existing proc-macro-error2 future-compatibility and debug/development/offline-mode
warnings remain. An initial Clippy test-literal style error was corrected before
the passing verification run.

Fork master is already an ancestor of the campaign branch. Fresh upstream master
and open dragon/steering/charging searches were inspected, including PRs 3407,
3661 and 4092. Their diffs do not change the default turn rate or the dying steering
call. Multipart/crystal/despawn work remains deferred to the overlapping PRs.
