# Silent dragon death sound

Pumpkin emitted the dragon death sound even for `Silent:1b` dragons. Two missing
pieces caused this: the dragon death tick ignored the silent flag, and the shared
entity NBT reader/writer did not load or preserve that flag. The fix restores
`Silent` through the existing tracked-data setter (default false when absent),
writes it only when true, and gates the first dragon death sound on that state.
This matches vanilla 26.3 `Entity.load`/`save` and `EnderDragon.tickDeath`.

The focused Rust regression checks the audible first tick, the silent first tick
and the surrounding death-sequence boundaries. The supporting fixture
`lab/examples/dragon-silent-state.json` checks summon state, preservation through
an unrelated NBT update, explicit clearing and clearing on key removal.

Validation: 457 `pumpkin-core` library tests, workspace formatting, core
all-targets/all-features clippy and a full debug Pumpkin build passed under the
shared lock, single Cargo job and required memory/CPU caps, with debug info and
incremental compilation disabled. The existing `proc-macro-error2`
future-compatibility warning remains.

The isolated protocol-777 comparison ran two repetitions per Silent value. A
player-attributed lethal hit followed by loading zero health isolates the death
animation from flight to the podium. Vanilla and patched Pumpkin passed 36/36
core checks. Baseline passed 32/36, failing only the two silent dragons' NBT-state
and death-sound assertions. Patched silent dragons sent no dragon death sound;
audible controls sent one at tick 1. No repeated dragon death sound was observed
at ticks 2–3. UUID corpse checks passed at tick 1 and removal checks at tick 200.

The committed NBT fixture passed 7/7 checks on vanilla and patched Pumpkin;
baseline passed 4/7, failing only the three Silent-state presence checks.
Combined results are vanilla/patched 43/43, baseline 36/43. Exact gameplay command
sequences and fixture hashes match across targets. All six scratch servers
stopped cleanly; logs contain no ERROR/panic lines. Client play entry, raw packet
captures, source hashes before/after the build and binary hashes were verified.
The final binary SHA-256 is
`a4efb404bb63a0ae8c58670d0a650d7b22e18a0a5c5f76536a5cd5e10bcab331`.
Raw evidence and provenance remain outside Git in `christine-dragon17-*` lab
artifacts. The initial post-death selector query, gate-only build and failed
launcher attempt are excluded from final validation.

Fork master `65bca3f` is included; upstream `b57d821` lacks these corrections.
Open PRs 3407/3661 concern other dragon behavior; 3720/3275 do not add this Silent
NBT wiring. Their patches were checked again before publication. Shared entity
load, summon, data and plugin NBT callers now restore the flag and its existing
tracked metadata. The other lane did not reserve or edit this shared source file.

Limits: headless server-state/packet evidence cannot prove client playback,
volume/range or visual animation. Pumpkin retains its positioned sound packet;
vanilla uses a global level event. Global delivery and generic living death
sounds remain independent follow-ups. Natural death flight, End portal creation,
save/reload and a complete fight were not exercised.

For a future human upstream contribution, kill isolated dragons with `Silent:1b`
and `Silent:0b`; expect no dragon death roar for the former and one roar as death
animation begins for the latter. Record both trials with audio before opening
any PR. This task opens no upstream PR or comment.

Next leads: reproduce global death-event delivery across distance/dimensions;
phase persistence needs actual resumed-AI evidence and correct phase-ID mapping,
including the missing sitting-scanning phase. Protected-block slowdown/in_wall
and dragon projectiles remain unconfirmed leads. Respect existing multipart PRs
and do not repeat completed contact, NoAI, initial-hover or XP-rule patches.
