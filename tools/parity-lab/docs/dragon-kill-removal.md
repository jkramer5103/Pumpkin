# Immediate dragon kill removal

Dragon command kills now remove the dragon immediately and skip its 200-tick
corpse animation and delayed death XP. This applies to living dragons and
existing corpses, with either NoAI value. Normal combat death still uses the
existing death sequence.

The vanilla reference is 26.3 `EnderDragon.kill`: immediate removal, entity_die,
and fight update/completion. The Pumpkin override removes parent and parts,
emits the existing game event, and calls the existing fight callbacks. The new
Mob kill hook preserves the previous generic_kill damage call for all other
mobs. Non-mob EntityBase implementations keep their existing dispatch.

Current upstream 998c3f8 has no intervening changes to these files since the
previous task. Fork master 65bca3f is already an ancestor. Open PR3407 a0cb2be
and PR3661 e7e5449 cover multipart registration and damage, without a dragon
kill override; this patch does not duplicate that work.

## Validation

The isolated protocol-client comparison checks immediate UUID absence without
advancing a tick, then absence and no XP through 201 ticks. It repeats live and
zero-health cases with both NoAI values twice. The permanent
`lab/examples/dragon-kill-removal.json` fixture covers all four combinations.
Cow controls verify that ordinary command kills retain zero-health corpses for
20 ticks.

Vanilla and patched Pumpkin each passed 100/100 focused checks. Baseline Pumpkin passed 68/100, failing
immediate/next-tick removal and absence of delayed XP as expected; the permanent
fixture independently reproduced removal and XP failures. The cow controls
passed on all three targets.

Workspace formatting, 458 core Rust tests, core all-targets/all-features clippy,
and the debug binary build passed under the shared Cargo lock, one build job,
no debug info/incremental, and the prescribed memory/CPU limits. The existing
proc-macro-error2 future-compatibility warning remains. Full raw reports and
source/binary hashes are retained in deployment artifacts. Assertions verified
equal stimuli, fixture/source/binary hashes, expected baseline failures, client
presence and server log checks. All six scratch server processes stopped; four
Pumpkin shutdowns completed. The two vanilla runs logged saving but lacked a
shutdown-completion marker within the existing harness grace period.

## Limits and client check

These arenas exercise command removal in the overworld, not a complete dragon
fight. Portal, gateway, egg, attached fight callbacks, multipart client behavior,
and game-event listeners are not proven by the focused comparison. Removal uses
the existing world removal API, which currently records Discarded. No rendered
client capture or sound playback proof is claimed.

For a real client check in a disposable arena: summon a dragon, run kill on its
UUID, and expect it to disappear immediately with no corpse ascent or delayed
XP. Repeat after forcing Health to zero. Capture a recording of both cases
before any human upstream submission.
