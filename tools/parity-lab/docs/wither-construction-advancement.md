# Wither construction advancement

Constructing a Wither should award Withering Heights to nearby players. The
previous `spawn_wither` path initialized the boss but never awarded its generated
`NETHER_SUMMON_WITHER` / `summoned` criterion. Command summoning does not use this
path and should not award it.

Vanilla 26.3 `WitherSkullBlock.checkSpawn` calls `SUMMONED_ENTITY` before adding
the boss, querying its bounding box inflated by 50 blocks. `EntityGetter` applies
`NO_SPECTATORS` to this query. The advancement data only requires a Wither entity;
there is no summoner, survival-mode, line-of-sight, parent-progress or dimension
requirement. Pumpkin's existing award helper handles progress, plugin completion
events and rewards. Generic custom advancement predicates remain outside the
existing static advancement system.

The focused world fixture covers near, diagonal beyond a 50-block sphere, just
inside/outside the intersecting player-box boundary, far, command-summoned,
Peaceful, missing-arm and spectator cases. A dispenser places the final skull
in isolated, frozen arenas with an exact protocol 777 headless observer.
Expected award outcomes come from the official 26.3 server, with grant/revoke
positive/reset controls. No rendered-client or whole-boss parity proof is claimed.

The Rust correction queries the constructed boss's expanded bounding box and
awards the existing generated criterion to intersecting nonspectator players,
before entity insertion. Existing construction gates and spawn events remain.

The isolated arena runs nine cases twice. Vanilla and patched Pumpkin both pass
190/190 checks. Baseline Pumpkin passes 184/190, missing only the six expected
awards for near, diagonal and just-inside players. The normal regression checker
fails on the baseline's first missing award. All three targets used identical
command hashes and 546 controlled ticks; source, copied-binary and fixture hashes,
cleanup, process stops and clean server/client logs were verified.

All 446 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and a debug server build passed under the shared Cargo lock and resource
limits. The pre-existing `proc-macro-error2` future-compatibility notice remains.
Initial selector-syntax discovery comparisons are excluded. Final observation
uses advancement revoke success after a grant/revoke positive control, without
selectors. Raw reports and investigation scripts remain outside the repository.

Rendered-client check still needed: construct a Wither near two survival players,
with an additional spectator nearby, and confirm that only the two nonspectators
receive Withering Heights. Capture the advancement toast and the construction.
Simultaneous multi-player audiences, rendered toasts, Bedrock, plugin-cancelled
spawns and custom-datapack criteria were not exercised.

Fork master was fetched and is already an ancestor. Upstream master remains
`fb7c8e223a387b9658c72eca620c81382dc66f07`; its construction path also lacks the
criterion dispatch. Live before/after proof uses the campaign branch, not a
separate upstream-master binary; unrelated upstream changes were not merged.
Fresh open-PR searches for Wither, summoning and advancements,
and relevant PR3835/4107/3887/4115 file reviews found no overlapping dispatch.
The [Mob AI tracking issue](https://github.com/Pumpkin-MC/Pumpkin/issues/3468)
and [tracker](https://pumpkinmc.org/tracker/) are leads; the tracked spawn-window
goal was already fixed in this branch and was not repeated.
