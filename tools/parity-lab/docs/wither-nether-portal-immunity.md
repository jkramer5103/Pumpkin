# Wither Nether portal immunity

Withers now reject Nether portal contact before destination lookup, portal events, cooldown refresh or transition scheduling. Full-health, powered and spawn-invulnerable bosses remain at their source portal, matching vanilla in the bounded regression. Other travelers retain their existing processing and cancellable event.

Vanilla 26.3 `NetherPortalBlock.entityInside` checks `entity.canUsePortal(false)` before calling `Entity.setAsInsidePortal`; `WitherBoss.canUsePortal` always returns false. Pumpkin called `Entity.try_use_portal` unconditionally. The Rust correction follows the existing End portal exclusion and changes only the Nether portal collision handler. Shared entity code is untouched.

The focused `wither-nether-portal-immunity.json` regression uses framed source portals and three NoAI/NoGravity boss states. It checks position, health, invulnerability and zero cooldown. A sheep must leave its source portal box; an away boss must stay put. Destination creation is left to each server. Ordinary-mob destination selection and dimension migration are outside this oracle.

Validation on two trials per target:

- Vanilla and patched Pumpkin each passed 28 gameplay assertions plus six client/environment/cleanup checks (34/34). Baseline passed 22/34, failing exactly the three boss position and three cooldown assertions per trial. Baseline moved each boss to `[-0.5,80,0.5]`; vanilla and patched retained the three source positions.
- Each trial advanced exactly 52 gameplay ticks through verified game-time barriers. Fixture and stimulus hashes matched across all three targets. Connected protocol 777 headless clients, boss/sheep spawn packets, cleanup, source/binary hashes and logs were checked. No server/client errors or panics were found.
- All 443 core Rust library tests, workspace format check, core all-targets/all-features Clippy and full debug server build passed under the shared Cargo lock with one job, debug info/incremental disabled, MemoryMax=5G, no swap and CPUQuota=200%.
- All three final scratch processes stopped; both Pumpkin save/shutdown completion markers were verified. Vanilla's full save completion marker was not observed within the harness grace period.

Evidence is retained in live lab artifacts `jaron-wither33-validation.json`, `jaron-wither33-verify.json` and `jaron-wither33-source-provenance.json`. Earlier setup/preload attempts are excluded. The first build attempt stopped at the 6 GiB disk preflight before Cargo; older own binaries were losslessly archived with decompressed hash verification before the successful rerun. Existing proc-macro-error2 future-compatibility, Java native/Unsafe, offline-mode and debug-build warnings remain.

Upstream master has the same unguarded Nether collision handler. Open Wither/portal PR searches were refreshed before publication; PR 4092 covers mob AI, PR 3835 projectile flight and PR 3865 death loot, with no equivalent portal exclusion. Fork master is already an ancestor; no relevant existing campaign patch required integration. The tracker and issue 3468 were leads only; completed spawn-goal fixes were not repeated.

Limitations: bounded portal contacts with NoAI/NoGravity and a private flat Nether on Pumpkin versus vanilla default Nether generation. No rendered client, full fight, portal generation/placement correctness, reverse traversal, mounts, plugin listeners or ordinary-mob dimension migration proof. The handler covers both directions by source inspection; only Overworld source contacts were exercised.
