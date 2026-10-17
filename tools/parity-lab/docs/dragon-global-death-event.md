# Dragon death event delivery

Pumpkin played the dragon death roar as a normal volume-1 positioned sound.
Vanilla 26.3 sends global level event 1028 on the first audible death tick.
Consequently, distant Pumpkin listeners missed the event, and disabling
`global_sound_events` did not give the vanilla local-event behavior.

The dragon now uses `World::sync_global_world_event`. That helper follows
`ServerLevel.globalLevelEvent`: global events reach players in every dimension;
in the source dimension their event position is projected to within 32 blocks
of the listener, while other dimensions use the listener's block position.
With the gamerule disabled, only listeners in the source dimension strictly
within 64 blocks of the event's integer block position receive a local event.
The existing Silent and first-tick gates remain in place.

A focused Rust regression covers position projection, negative-coordinate
flooring, cross-dimension selection and the strict 64-block local boundary.
The helper's other caller is End portal creation (event 1038); vanilla
`EnderEyeItem` also uses `globalLevelEvent` there. Its delivery uses the corrected
helper, but portal activation itself has not been separately live-tested.

The bounded isolated protocol-777 reference comparison repeats nearby and
96-block distant listeners, local delivery near and 48 blocks away, an excluded
distant local listener and a silent control. Vanilla passed 96/96 checks;
baseline Pumpkin passed 88/96, failing the eight expected delivery checks.
The baseline binary corresponds to source commit `3fa600fdf9dcc149ffb960eecaab8c66c4c8309a`.
Both reference servers stopped. Commands and listener positions match.

All 458 `pumpkin-core` library tests, workspace formatting, core all-targets/
all-features clippy and the full debug Pumpkin build passed under the shared
build lock, single Cargo job and required memory/CPU caps. Debug info and
incremental compilation were disabled. The existing `proc-macro-error2`
future-compatibility warning remains. The core patched replay passed 96/96
checks, matching vanilla. The final cross-dimension comparison uses a second
stationary player in the source world and verifies the dragon is present before
and after death tick 1. Vanilla and patched Pumpkin passed 44/44 checks; baseline
passed 42/44, missing both global events for the Nether listener. With global
sounds disabled, that listener received no event on all three targets.

Combined results are vanilla/patched 140/140 and baseline 130/140. Exact gameplay
commands, listener positions, event types, global flags, event positions and
absence of repeated events at ticks 2–3 were checked. Source hashes before and
after the build and replay binary hashes match. The binary SHA-256 is
`c3bb3cd72f0464a02ccc77dc74a6886460ddf285ed2fde541e814e216cd9808d`.
All six final server processes stopped and their logs have no ERROR/panic lines.
Five have completed-shutdown markers; the patched cross-dimension server logged
shutdown initiation but not completion before the scratch console's eight-second
grace expired. Its clean shutdown is unverified, and this task does not fix it.

The initial unanchored dimension runs cannot distinguish entity unloading from
event delivery and are excluded. One anchor startup used the wrong port from
the generated config; that failed run is excluded. The final fixture reads the
Java game port explicitly. The initial compile error and preliminary interrupted
client run are also excluded. No source changes were needed after the passing
Rust build to resolve these fixture issues.
Raw evidence remains in the lab's `christine-dragon18-*` artifacts outside Git.

Fork master `65bca3f` is already integrated; upstream `b57d821` retains the bug.
Open PRs 3407/3661 address dragon parts, 3739 ordinary sound range, and 3221
generic living death behavior. None supplies this global dragon event fix.

Limits: headless packet capture does not demonstrate client audio playback or
visual animation. Natural death flight, save/reload, portal creation and a whole
boss fight are outside this comparison. Before any future human upstream
contribution, record an isolated dragon death with nearby and distant listeners,
then repeat with `global_sound_events false`; check the audible result and attach
a real client recording. No upstream PR or comment is opened by this task.

A separate lead is source-chunk survival when the last viewer changes dimension:
inspect unload/forceload handling and PRs 3407/3661, then reproduce it with direct
entity-presence observations before claiming a new defect.

Next candidates remain phase persistence with correct phase IDs and observable
resumed AI, protected-block flight slowdown, and dragon projectiles. Recheck
upstream overlap and reproduce each separately. Do not repeat the completed
contact, NoAI, initial-hover, XP-rule or Silent fixes.
