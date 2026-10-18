# Wither Silent state and sound events

Pumpkin's base entity NBT reader ignored `Silent`, and its writer omitted the
state. A Wither summoned or restored with `Silent:1b` therefore still emitted
its spawn-completion and skull-firing events. This was observed separately during
the earlier spawn-sound task; that task explicitly excluded the failing control.
The current task reserves the shared entity file and the Wither file, with no
other lane holding either reservation.

The base entity now restores Silent through the existing synchronized setter,
defaults it to false when absent, and saves it only when true. This follows vanilla
26.3 `Entity.load`/`saveWithoutId`: removing the key also re-enables sound. Existing
Wither spawn and shooting guards consume that state. Retaliation event 1022 stays
unconditional after an actual block break, matching `WitherBoss.customServerAiStep`;
its old Silent guard would suppress that event once the flag became effective.
The block-break helper, plugin events, loot and mob-griefing gate are preserved.
No plugin event exists on the Silent setter or these level-event sound paths.

This shared base-state correction applies to every entity using the NBT reader and
writer. The bounded gameplay comparison covers Withers. It does not establish
that every other mob's individual sound emitter respects Silent.

`lab/examples/wither-silent-sounds.json` exercises audible and silent spawn
completion, flag updates, flag removal, natural skull firing, delayed retaliation,
and no-break/mob-griefing controls in a disposable forced-loaded arena. Each case
clears entities and advances a cleanup barrier before creating its boss. A
connected protocol-777 client records actual level events alongside the fixture's
NBT/block observations. Run this fixture with packet capture; command checks alone
do not verify sound dispatch.

All 444 existing core Rust library tests, workspace formatting, core all-targets/
all-features Clippy and the debug server build passed under the shared Cargo lock,
one build job, disabled debug info/incremental compilation and the required
5-GiB/no-swap/200%-CPU scope. The copied binary and both source hashes match the
verification record. This gameplay regression is covered by the live fixture;
no synthetic entity/world mocks were added to the Rust unit suite.

Two final identical-fixture trials passed 212/212 checks on vanilla and patched
Pumpkin. Baseline `f51b139fc95dd3d5b364cd6f3b1dae7bed1a45a7` passed 194/212,
with exactly 18 expected failures: six spawn/firing event checks and twelve
Silent-state observations. The comparison exercised 1,040 controlled ticks per
target. Audible and Silent bosses both fired real skulls; Silent only suppressed
the firing event. Successful retaliation emitted one local event 1022 at
`(8,80,8)` for both bosses; no-break and disabled-mob-griefing controls emitted
none. Spawn completion emitted event 1023 only when audible; shots used 1024.
Both flag updates and removing Silent were exercised.

The final assertions verify identical fixture and gameplay-command hashes,
controlled ticks, connected clients, clean entity cleanup, source/binary hashes
and exact expected baseline failures. Each client's packet log contains all 22
Withers and actual Wither skull spawns. All three scratch processes stopped;
both Pumpkin saves and stops completed. Final server/client logs have no ERROR,
panic or uncaught-thread-exception lines. Vanilla full-save completion was not
verified within the harness shutdown grace. Expected console fence probes for
unknown temporary scoreboard objectives are harness traffic, not gameplay proof.
Raw reports and final assertions are local `artifacts/jaron-wither44-silent-*`
evidence, outside Git.

Initial samples exposed unrelated vertical drift despite `NoGravity:1b`. The final
fixture teleports the boss before each retaliation tick to isolate the sound
position. Earlier fixture/enum corrections, drifting-position samples and a run
interrupted by a mid-record packet-read offset are excluded. The scratch reader
now captures at newline boundaries. The last post-run assertion initially used
incorrect save/stop message strings; actual logs show `Completed save!` and
`The server has stopped.`. Correcting those strings passed all evidence checks
without rerunning or altering gameplay results.

Fork master was fetched and is already an ancestor of the campaign branch.
Current upstream still omits the base Silent load/save and retains the extra
retaliation guard. The tracker and Mob AI issue #3468 were reviewed; earlier
spawn-window fixes are complete. The final open-PR refresh found no duplicate Silent correction; PR heads
#4092, #4107 and #3835 were unchanged and do not provide this correction. The initial healing/harming candidate was abandoned because
#4107 already implements it; its experimental results are not evidence for this
sound fix. No upstream write action was taken.

There is no rendered-client or audible-playback recording. A human can verify in
a scratch arena: compare normal and Silent Withers completing their charge and
firing skulls, toggle/remove Silent, and damage a Silent Wither next to dirt. The
first sounds should follow Silent; the delayed block-break event should still
play when dirt actually breaks. Full fights, other mobs, Bedrock, plugin listeners
and a save/restart round trip are outside the current bounded comparison.
