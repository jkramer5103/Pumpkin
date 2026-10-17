# Restore saved dragon flight phases

Pumpkin discarded `DragonPhase` on NBT reads and writes. A dragon restored with
vanilla's holding-pattern state therefore kept the constructor's hovering phase
and did not resume flight. The dragon NBT hooks now restore implemented phases
through `set_phase`, preserving phase begin/end behavior, and save vanilla phase
IDs. Missing input leaves the current phase alone; invalid IDs select holding
pattern, matching vanilla's `EnderDragonPhase.getById`. Death progress is loaded
after the phase transition, because entering the dying handler resets its timer.

Pumpkin's internal discriminants differ from vanilla IDs. Translation keeps
phase-manager array indexing internal. Pumpkin's extra `FlyToPortal` step saves
as vanilla landing approach (2). Vanilla sitting scanning (6) has no Pumpkin
implementation and is explicitly left unsupported; input 6 preserves the current
phase. This patch does not implement scanning or repair other phase algorithms.

Reference: Mojang 26.3 server `EnderDragon.readAdditionalSaveData`,
`addAdditionalSaveData`, `EnderDragonPhase`, and `EnderDragonPhaseManager`.
Read-only upstream checks found master 998c3f8 unchanged in the affected paths.
[PR3407](https://github.com/Pumpkin-MC/Pumpkin/pull/3407) at a0cb2be and
[PR3661](https://github.com/Pumpkin-MC/Pumpkin/pull/3661) at e7e5449 concern hitboxes
and damage, without phase persistence. Fork master 65bca3f is already integrated.

Initial headless protocol 777 comparison: two trials per state. Over five frozen
and explicitly advanced ticks, vanilla phase 0 moved about 0.84 blocks while
baseline cac2612 moved 0.044 and remained hovering. Vanilla phase 10 moved 0.070;
missing-phase controls behaved the same. Invalid IDs -1 and 11 resumed vanilla's
holding pattern but stayed hovering on baseline. The permanent fixture checks
movement outside a 0.15-block radius, plus hovering inside it, after five ticks.

All 460 pumpkin-core library tests, workspace formatting, core all-targets and
all-features clippy, and the debug Pumpkin build passed under the shared Cargo
lock and resource limits. The first clippy run found a redundant match arm; that
arm was removed before the passing rerun.

Vanilla and patched Pumpkin each passed 69/69 focused checks; baseline passed
26/69, with 43 expected restoration and flight failures. The replay used identical
commands, verified tick barriers, source/binary hashes, and an unchanged permanent
fixture. Two trials cover holding pattern, hovering, absent phase, and invalid
IDs -1 and 11. NoAI controls cover serialization of the other implemented vanilla
phase IDs, changing phase through NBT merge, and retaining the current phase when
the field is removed. These controls do not validate those phases' AI algorithms.

All six scratch processes stopped; four Pumpkin shutdown completion markers were
verified. The two vanilla runs logged saving but no completion marker within the
existing harness grace. Server and headless-client logs showed no panic or error.
No disk restart, natural End fight, exact flight trajectory, rendered-client, or
full fight proof is claimed. Sitting scanning (6) remains unsupported. The baseline
binary was built for task 21 with the same Rust source as cac2612; source/binary
hashes are retained in task 21 provenance. Existing proc-macro-error2 future
compatibility warnings remain unrelated to this patch.
