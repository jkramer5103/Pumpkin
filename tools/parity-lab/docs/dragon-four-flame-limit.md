# Perched dragon flame attack budget

A dragon that repeatedly breathes while perched should leave after its fourth
flame. Before this patch Pumpkin always returned to sitting scanning, so it could
keep attacking from the podium without the fourth-flame departure.

Reference: Minecraft 26.3 `DragonSittingFlamingPhase.begin` increments the attack
count on entry, and `doServerTick` chooses takeoff at flame tick 200 once the count
reaches four. `EnderDragonPhaseManager` does not reenter an unchanged phase.
`DragonLandingPhase` resets that count when landing completes. The counter is
runtime state, independent for each dragon, and is not written to NBT.

The Rust change keeps a per-dragon flame count, counts actual breathing entries,
selects takeoff at the fourth completion, and resets the count at the existing
landing completion into scanning. It preserves flame cleanup and the existing
200-tick breathing schedule. Landing flight and takeoff navigation are separate
existing limitations; this patch does not establish that their trajectories
match vanilla. In particular, Pumpkin currently completes landing immediately;
the reset lives at that completion site rather than on unrelated phase changes.

## Regression scenario

`lab/examples/dragon-four-flame-limit.json` runs two isolated trials using
persistent dragons and a creative headless observer. Each checks:

- Flames one through three scan after completion; flame four is still active
  at tick 199 and selects takeoff at tick 200.
- Merging the current phase does not spend another attack, and NoAI pauses the
  fourth flame at its final tick.
- A separate dragon still finishes its first flame by scanning.
- Landing at a controlled podium top restores the original dragon's attack
  budget so its next flame ends in scanning again.

## Validation

Final checks passed under the shared Cargo lock with one build job, disabled
debug information and incremental compilation, and the required 5 GiB/no-swap/
200% CPU scope:

- `cargo fmt --all -- --check`
- `cargo test --locked -p pumpkin-core --lib`: 473 passed.
- `cargo clippy --locked -p pumpkin-core --all-targets --all-features`
- `cargo build --locked -p pumpkin`

The Rust boundary regression fails when the old unconditional scanning decision
is restored with the test retained. This is a decision-level regression check,
not a complete build of the old tree.

The same two-trial fixture produced:

| Target | Checks passed |
| --- | --- |
| Vanilla 26.3 | 59/59 |
| Source baseline `ce9e88d` | 57/59 |
| Patched source | 59/59 |

Baseline failed only the two fourth-flame takeoff observations. Every target
advanced 2,408 controlled ticks. Fixture, source, copied-binary and input hashes
were checked; input sequences matched after excluding read-only time polling.
All three scratch processes stopped without logged server errors or panics.
Both Pumpkin saves completed. Vanilla's final save completion marker was not
verified within the shutdown grace period.

The first launcher exited before Cargo because its service PATH omitted Cargo;
the first valid run then stopped at Clippy's const-function lint. The final run
includes that correction and all four passing Rust checks. Existing
`proc-macro-error2` future-compatibility and debug/offline-mode/native-access
warnings remain. Local artifacts retain raw reports, hashes and logs; downloaded
or decompiled Java is not published.

Open upstream Dragon fixes were checked for overlap. Hitbox, damage, despawn and
crystal work in PRs 3407/3661 and fireball work in PR 3835 are separate; none of
the inspected patches implements this flame budget.

Headless phase and server-state checks cannot prove rendered animation, a whole
boss fight, natural landing flight, the subsequent takeoff trajectory, or audio.
A real-client check should observe four perched flame attacks followed by
flight, then a fresh budget on the next completed landing.
