# Wither End portal immunity

Wither contacts with End portals must leave the boss at its contact position. Vanilla 26.3 `WitherBoss.canUsePortal(false)` returns false. `EndPortalBlock.entityInside` checks that predicate before setting the portal processor. Pumpkin's block collision previously called `try_use_portal` for Withers. In an isolated, preloaded arena the baseline moves full-health, powered and spawn-invulnerable bosses to the End platform coordinates `(100.5, 50, 0.5)`.

The correction rejects Wither contact at the End portal block before looking up the destination world or invoking portal processing and its plugin event/cooldown side effects. Ordinary entities follow the existing path. The completed gateway exclusion is separate; Nether portal eligibility is outside this correction.

## Regression and provenance

`lab/examples/wither-end-portal-immunity.json` covers three boss states, a sheep portal contact and a Wither away from portals. NoAI and NoGravity isolate portal contact from attacks, movement and regeneration. The runner uses the existing headless protocol 777 client, deterministic tick barriers and engine lock. Both destination and source chunks are preloaded. The Pumpkin End destination uses a private flat generator to avoid unrelated noise-generation stalls; vanilla retains its default End generator. The earlier exploratory and stalled noise-generation runs are excluded from final evidence. Each final trial advances 52 gameplay ticks, apart from cleanup/preflight ticks. Reports retain exact fixture, gameplay stimulus, source and binary hashes.

Two clean repetitions: vanilla/patched 28/28 focused checks; baseline 22/28, failing exactly the six expected Wither position checks. All six baseline contacts move the boss to `(100.5,50,0.5)`; vanilla and patched Pumpkin retain the three original contact positions. All three targets pass boss health/invulnerability, sheep source-box exit, away-boss, client presence and cleanup controls. Identical fixture/gameplay command hashes, 104 gameplay ticks per target, stopped processes, connected headless clients, observed boss/control spawn packets and error-free logs verified. Fewer boss spawn packets were observed on baseline; complete actor visibility is not claimed. All three scratch processes stopped; both Pumpkin save/shutdown completion markers were verified. Vanilla full save completion was not verified within the existing shutdown grace. Existing Java native/Unsafe and offline/debug-mode warnings remain.

The exact final source passed workspace formatting, 443 core library Rust tests, core all-targets/all-features Clippy and a full debug server build. Commands: `cargo fmt --all -- --check`, `cargo test --locked -p pumpkin-core --lib`, `cargo clippy --locked -p pumpkin-core --all-targets --all-features`, and `cargo build --locked -p pumpkin`. Cargo ran under the shared build lock with one build job, debug info/incremental disabled, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. Existing `proc-macro-error2` future-compatibility warnings remain. Local evidence: `artifacts/jaron-wither32-verify.json`, `artifacts/jaron-wither32-validation.json`, `artifacts/jaron-wither32-source-provenance.json`.

## Scope and limitations

This is a bounded Wither End portal contact regression, not a full boss fight or rendered-client capture. The ordinary sheep control proves it leaves the source portal box; it does not claim correct dimension transfer. Source inspection indicates the shared default non-player teleport path changes coordinates without changing the world reference; ordinary-mob dimension migration remains outside this validation and correction. Natural portal construction, Nether portals, the End exit direction, mounted entities and plugin listeners are not covered by this arena. No new general entity eligibility API is introduced.

## Upstream review

Read-only fork/upstream fetches and open Wither/portal PR searches completed before edits. Fork master `65bca3f` is already an ancestor of this lane; no integration is pending. Upstream `998c3f8` still has the same unguarded End portal collision. Reviewed PR 4092 (mob AI), 3835 (projectiles), 3865 (star death), 3407 (dragon parts); none supplies this Wither End portal exclusion. The mob AI tracker 3468 is a lead, and its invulnerability/ranged-goal items have already been addressed by earlier campaign patches. No upstream publication was made.

## Manual client follow-up

In a disposable world with an End portal, place a full-health Wither, a powered Wither and a spawn-invulnerable Wither against the portal. Each boss should stay on its original side. An ordinary sheep should still enter the portal. Record a real client showing the boss contacts if visual review is needed; no rendered-client capture was produced by this task.
