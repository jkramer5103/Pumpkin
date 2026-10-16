# Autonomous fork work

The user explicitly said to let both agents fix Pumpkin and push to their fork.
They confirmed both processes should run in YOLO mode. This supersedes the initial
task's prohibition on publication and restriction to lab files for Pumpkin work.

- Authorized push destination: `https://github.com/jkramer5103/Pumpkin.git` ONLY.
- `upstream` is read-only `https://github.com/Pumpkin-MC/Pumpkin.git`.
- Campaign branch containing the lab: `parity-lab`.
- Christine worktree: `/root/pumpkin-parity-worktrees/christine`, branch
  `parity-lab-christine` (engine, RCON, execute/scoreboard commands).
- Jaron worktree: `/root/pumpkin-parity-worktrees/jaron`, branch
  `parity-lab-jaron` (blocks, entities, world loading and provisioning).
- Worktrees start from the current upstream master, not an old binary release.
- Inspect upstream AGENTS.md and scoped AGENTS.md before code changes. No PRs.
- Inspect open upstream fixes for overlap, but the user's fork may integrate
  existing fixes if useful. Record attribution and source commit when doing so.
- Do not force-push or rewrite/delete unrelated branches. Commit and push your
  own fixes autonomously once ready. Keep granular commits with clear messages.
- Never commit credentials, target configs/passwords, logs, worlds, downloaded
  jars, decompiled Java, or artifacts. Publish only original lab code, scenario
  definitions, documentation, and appropriate Pumpkin patches/tests.

## Baseline and validation

The released binary is an older baseline. Reproduce findings on current upstream
before labeling them new Pumpkin defects. A build of current code takes priority
over generating hundreds of cases blocked by an old command capability.

Use a shared build target `/root/pumpkin-parity-worktrees/target` and serialize
ALL cargo operations with `flock /root/pumpkin-parity-worktrees/build.lock`.
Always use `CARGO_BUILD_JOBS=1`, debug info disabled and incremental disabled.
Run heavy cargo under a systemd scope with `MemoryMax=5G`, `MemorySwapMax=0`,
`CPUQuota=200%`; do not start a second build alongside it. Check disk first;
keep at least 6 GiB free. Do not delete unrelated caches or build targets.
Prefer relevant crate checks/tests before a full binary build. A patch pushed
with incomplete validation must plainly say so in docs/ findings; never claim
the existing released test server validated a source-only patch.

The first successful current binary can replace only the lab's Pumpkin candidate.
Hold the engine run lock before stopping/restarting that service. Back up its
manifest/config, record the exact source commit and build command in the runtime
manifest, then run the same relevant scenarios against vanilla and the new binary.
No test-world migration risks affect unrelated servers: these are lab-only worlds.

## Integration

The coordinator publishes lab files on `parity-lab`. Push patch branches separately
as you make progress, and add concise evidence/finding documents under
`tools/parity-lab/docs/` in your worktree. Do not merge into or push master.
Update the live `artifacts/<account>-fork-status.json` (safe JSON, no secrets)
with `branch`, `head`, `pushed_at`, `validation`, `findings`, and `limitations` so
the dashboard can show what was actually pushed. No unsupported claims.

The user wants concise patch summaries instead of live commands. Also include
`patches`, an accumulating list of objects with `commit` (full hash), `title`,
`summary` (one or two plain sentences explaining the behavior fixed),
`validation` (brief actual checks plus limitations), and `validated` (true only
when the fix has meaningful passing validation). Keep all earlier patch entries.
The dashboard cross-checks commits and pushed branches against Git itself.

Do not spend inference repeatedly polling an active compiler or a test waiting
for the shared build lock. If no independent useful work remains, checkpoint:
`python3 ops/wait-for-build.py --account YOUR_ACCOUNT --unit BUILD_OR_TEST.scope --reason "short reason"`
Then finish the turn. The supervisor keeps the same thread and waits without
inference until that exact scope exits, then resumes you to inspect its result.

Continue the finite queue, prioritizing real fixes over cosmetic test growth.
