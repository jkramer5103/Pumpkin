# Wither nether star lifetime

Vanilla 26.3 `WitherBoss.dropCustomDeathLoot` gives its nether star
`ItemEntity.setExtendedLifetime()`, starting item age at -6000. Ordinary items
start at 0; both expire at 6000. A boss drop therefore lasts 12000 simulation
ticks (ten minutes at the default rate).

Pumpkin created an ordinary item. Its unsigned item age also converted loaded
negative ages to large positive values, despawning a restored extended drop on
its first tick. The initial isolated comparison reproduced both problems:
vanilla's star age was -5998 after two ticks; Pumpkin's was 1. A restored -6000
star survived on vanilla and disappeared immediately on Pumpkin. The ordinary
5998 -> 5999 -> removal control passed on both.

The correction gives both existing Wither drop sites the extended lifetime and
stores item age as a signed integer, including NBT restoration and minimum age
selection during merges. `World.create_item_drop` prepares the same randomized
item and cancellable spawn event used by `drop_stack`, allowing the Wither to
set its age before spawning. Ordinary callers retain their existing interface,
position, velocity, pickup delay and event behavior.

The focused regression is `lab/examples/wither-nether-star-lifetime.json`.
It checks an actual death drop's negative starting age, normalizes the existing
one-tick difference in drop scheduling, then advances 12000 measured simulation
ticks alongside an ordinary nether star. The extended drop must survive the
five-minute mark, remain at age 5999 just before ten minutes, and disappear on
the next tick. Negative-age summon and data-merge restoration are also checked.
A 1000-tick rate accelerates this bounded scratch-world simulation; it is restored
to 20 in cleanup. A connected protocol 777 headless observer stays outside pickup
range. The same fixture runs twice on each target.

Validation on 2026-10-18:

| Target | Passing checks | Trials |
| --- | ---: | ---: |
| Vanilla 26.3 | 40/40 | 2 |
| Pumpkin baseline `839e15f8307db7703af2bdc99208618c48049be4` | 28/40 | 2 |
| Patched Pumpkin | 40/40 | 2 |

Each trial advances 12006 verified ticks for the measured scenario. Baseline
fails exactly six checks per trial: negative starting age, three extended
lifetime boundaries, and two negative-age NBT restoration checks. All ordinary
item controls pass. Identical fixture and gameplay-command hashes are verified.
The fixture uses direct NBT predicates; the initial unsupported execute-store
probe is excluded from this final comparison.

All 444 existing `pumpkin-core` library tests, workspace formatting, core
all-targets/all-features Clippy and the debug server build pass. Cargo operations
used the shared build lock, one job, disabled debug info/incremental compilation,
and the required 5 GiB/zero-swap/200% CPU limits. Source and copied-binary hashes
match the verification record. The build retains the existing
`proc-macro-error2` future-compatibility warning.

Both Pumpkin scratch servers completed saves and stopped; the vanilla process
stopped with an RCON listener shutdown marker. Vanilla full-save completion is
not established by that marker. No server/client errors or panics were found.
Raw evidence stays outside the repository in
`artifacts/jaron-wither41-validation.json`, `artifacts/jaron-wither41-verify.json`,
and `artifacts/jaron-wither41-final-logs.json` in the deployment workspace.

Open upstream PR #3865 addresses death-drop timing/gamerule handling; PR #4105
addresses mob_drops. Neither adds extended lifetime. PR #4054 changes item merging
without signed age storage. PR #3936 exposes item drop positions. These separate
changes are excluded. The passive-healing bossbar ordering candidate was skipped
because PR #4092 already corrects it. Tracker and issue #3468 are investigation
leads, not proof of the behavior fixed here.

The existing death callback timing, drop position, mob_drops gate and experience
behavior are unchanged. Plugin listeners, full boss fights, real-time duration,
rendered clients, Bedrock and an actual world unload/reload are not verified.
NBT restoration is exercised through summon and data merge. The shared signed
age correction also applies to other negative-aged dropped items; it does not
implement vanilla's separate infinite-age sentinel behavior.
