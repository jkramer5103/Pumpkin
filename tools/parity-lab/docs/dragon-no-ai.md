# Ender Dragon NoAI gameplay gate

A dragon with `NoAI:1b` previously continued running Pumpkin's phase, steering,
contact and block-destruction code. It pushed and damaged an overlapping player
and removed a stone block that vanilla preserved. The correction checks NoAI
after crystal healing and before flight history, phase work, part updates,
contact and walls, following vanilla 26.3 `EnderDragon.aiStep`. It also pins flap
time to 0.5. Shared living movement already skips travel for NoAI mobs.

Pumpkin runs its existing death animation inside the Dying phase, which can
temporarily restore one health. That phase remains outside the NoAI gate so
killed NoAI dragons still complete their existing sequence. Changing NoAI through
the normal mob NBT path takes effect on the next tick. No shared entity or combat
code changes.

Fork master `65bca3f` is already an ancestor. Upstream master `5b53f06` still lacks
the gate. Open PRs 3407/3661 concern parts, incoming damage, crystals and fight
state; 4080 concerns team damage; 3793/3794 concern touch and velocity. Inspected
patches and the final open-dragon search contain no equivalent NoAI correction.
Leads: [Mob AI tracking](https://github.com/Pumpkin-MC/Pumpkin/issues/3468) and
[parity tracker](https://pumpkinmc.org/tracker/).

Source commit: `9dc344aaa803700b58c6e1414cf7b5780cc3f519`.

The final revision passes all 456 pumpkin-core library tests, workspace
formatting, core all-targets/all-features clippy, and a full Pumpkin binary
build. Cargo used the shared lock, one job, disabled debug info/incremental,
MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. Source hash and build-parent plus
Rust diff are recorded in `artifacts/christine-dragon14-final-rust-validation.json`.
Immutable binary SHA-256:
`a9328a0e127b3d9c517144cea54fc51936d2c1586aa37ffcbbbf874da1b03368`.

The isolated comparison uses a loopback protocol-777 headless player, one dragon
at a time, a bounded loaded arena and frozen/stepped ticks. Two repetitions
check NoAI suppression and resumption after removing NoAI. Each sample begins
with the dragon at (8,80,8), the player at (12,80,8), zero horizontal player
motion, and confirmed removal of the previous dragon. After exactly three ticks:

| State | Vanilla | Baseline | Patched |
| --- | --- | --- | --- |
| NoAI: overlapping stone | Preserved | Removed | Preserved |
| NoAI: horizontal contact impulse | Absent | Present | Absent |
| NoAI: player health, starting at 20 | 20 | 15 | 20 |
| NoAI removed: stone destruction and contact impulse | Resume | Resume | Resume |

The committed fixture
`tools/parity-lab/lab/examples/dragon-no-ai-block-destruction.json` additionally
sets NoAI again on the same dragon and checks block protection returns. A
separate control confirms healing remains active with NoAI: vanilla health
100 to 104 and both Pumpkin binaries 100 to 160 after 60 ticks. This confirms
healing presence, not cadence parity. All targets also pass eventual dragon
absence checks after 210 cleanup ticks. Core and control sessions use separate
clients to stay within the existing client's event cap.

Vanilla and patched each pass 39/39 focused checks; baseline passes 30/39.
Its nine failed checks are the repeated NoAI contact/health/block observations
and additional block-preservation controls. These are repeated observations of
this bounded defect, not nine separate bugs. Fixture command hashes match
across targets after excluding variable read-only game-time polling. Starting
positions, tick deltas, player presence, source/binary provenance and all six
accepted scratch-server logs pass their controls. No server ERROR/panic or
client event-cap/exception diagnostics were found. All six servers stopped.

The first patched binary passed compilation but froze its death sequence when
that sequence restored one health. It is excluded; final cleanup checks cover
the phase-aware correction. Valid vanilla/baseline references are reused from
that run. Their raw successful client-presence response is exactly
`Test passed. Count: 1`; the first checker incorrectly expected `Test passed`.
The corrected assertion reads the retained raw response without changing it.
Earlier motion assertions that counted falling Y as contact and active-contact
health expectations are excluded. Active-contact health remains different in
this fixture: vanilla 20 versus Pumpkin 15. Only NoAI health preservation and
active impulse/block resumption are parity claims.

Local evidence: `artifacts/christine-dragon14-live-validation.json`, the final
Rust record, and raw reports `christine-dragon14-live-20261016T173819.869656Z`
/ `174143.125437Z` (vanilla/baseline only) and `175219.329760Z` /
`175317.159703Z` (final patched binary). Logs, worlds and decompiled source stay
outside the repository.

Limits: part dimensions/registration, perched volumes, phase IDs/persistence,
crystal selection/healing cadence, death timing and complete fights remain
separate work. Phase/history suppression and flap pinning are reviewed against
vanilla source. There is no real-client visual, prediction or exact Motion proof.

Real-client follow-up in an isolated arena: summon a NoAI dragon over a stone
block overlapping its body. Approach its wing in survival mode; expect no dragon
contact push or damage and an intact block. Remove NoAI; expect destruction and
push to resume. Set NoAI again; expect those effects to stop. Record the gameplay
to check client visuals independently of these server-state results.
