# Server lifecycle and reproduction audit

Audit date: 2026-10-16. Scope: only the two private parity-lab services.
No world reset or credential rotation was requested or performed. Existing source
fixes remain on `parity-lab-jaron`; this campaign changes lab infrastructure.
Upstream master was rechecked with `git ls-remote upstream refs/heads/master`:
`5b53f064af8708ba33fcaa533b81ca29a53a3310`, matching the previously built baseline.
That baseline has no RCON; the active candidate is the verified official release.

## Changes and reproductions

- **Preserve existing blocks during readiness.** `control()` previously placed
  stone at `2 64 2` and then replaced it with air on every provision/start/restart.
  A live vanilla diamond-block sentinel was erased by that old code. The original
  air block was restored, and the raw reproducer is retained in
  `artifacts/jaron-lifecycle-red.json`. Readiness now verifies RCON and gamerules
  without writing blocks. It still applies the documented time/weather/spawn and
  force-load controls, and saves the world.
- **Restore deployment provenance on failure.** Candidate rollback now restores
  the backed-up manifest as well as config and service override, and verifies
  recovered RCON/gamerules. An injected failure after manifest replacement
  reproduces stale provenance in the old implementation, both with and without
  an existing service override. The fixed implementation passes both cases.
  This failure-injection check is isolated and does not deploy a candidate live.
- **Keep provisioning reproducible.** Request the reviewed Pumpkin release by
  tag rather than `releases/latest`. The release tag, Mojang metadata checksum,
  binary checksums and GitHub asset digests remain verified. New releases cannot
  silently upgrade this lab or prevent reuse of the reviewed pin. Archive names
  now have microsecond precision to avoid same-second reset-name collisions;
  destructive reset flags were not exercised live.
- **Report normal vanilla stops correctly.** The JVM exits 143 after SIGTERM.
  The old unit reported that normal stop as failed; original journal evidence is
  `artifacts/jaron-lifecycle-vanilla-stop-red.log`. Only vanilla now accepts
  status 143 as successful. Repeated stops reach `inactive` with no lab listeners.
- **Retain control evidence.** Authenticated readiness command transcripts have
  timestamped private copies in `runtime/control-evidence/`. The existing
  bootstrap filenames continue to refer to the latest attempt.

## Exact recovery commands and validation

Normal commands, from `/root/pumpkin-parity-lab`:

```sh
python3 infra/provision.py
python3 infra/provision.py
infra/servers stop both
infra/servers stop both
infra/servers start both
infra/servers start both
infra/servers restart both
python3 -m unittest discover -s tests -p 'test_scenarios*.py' -v
python3 -m unittest discover -s tests -q
```

All mutating entry points acquire the engine's process file lock
`/tmp/pumpkin-parity-lab-0.lock` as root. Provisioning additionally takes
`runtime/provision.lock`. Keep the lock file in place; unlinking it can allow
overlapping locks on different inodes. `lifecycle.transition()` is an internal
helper whose caller must already hold that engine lock; use the CLI for normal
operation.

The instrumented live sequence ran with:

```sh
timeout --signal=TERM --kill-after=30s 600s python3 artifacts/jaron-audit-lifecycle.py
```

The retained local script holds both locks across sentinel setup, two calls to
`provision.provision(Namespace(reset_worlds=False, rotate_credentials=False))`,
the five lifecycle transitions above, verification and cleanup. It uses the same
transition implementation as the CLI. `artifacts/jaron-lifecycle-recovery.json`
records **57/57 checks passing**, `complete=true`, and cleanup completed.
Both servers recovered. Checks verify unchanged credential-file bytes and mode
0600, world directory inode and private marker preservation, vanilla saved block
and scoreboard persistence, all four listeners restricted to loopback, and cached
binary checksums. Sentinels and markers were removed and saved afterward.

The two new unit tests fail against the previous published lab snapshot
`d6d88faa453f3c46d3cfa1fe9da675bbb694c209` (three failures, including both rollback
subcases), then pass with the fixes. Logs are
`artifacts/jaron-lifecycle-unit-{red,green}.log`. The assigned suite passes
24 tests; the full suite passes 107 tests. Existing tests were retained.
The module CLI was also tested while `lab.runner.process_lock()` was held: it
waited without issuing readiness commands, then succeeded after lock release.
Evidence: `artifacts/jaron-lifecycle-lock.json`.

After recovery, the full static catalog was run twice under the engine lock:

```sh
timeout --signal=TERM --kill-after=30s 600s python3 -m lab run \
  --targets runtime/targets.json --scenarios scenarios \
  --output artifacts/jaron-lifecycle-catalog --repeat 2 --timeout 3 --lock-timeout 30
```

It completed all **96 scenarios / 192 trials** and exited **2**:
**0 pass, 23 different, 73 error**, no flakes and no confirmed mismatch claims.
Vanilla satisfied all **192/192 positive expectation sets**, with no transport
errors; four target trials still report intentional failed-command problems.
The released Pumpkin satisfied **0/192** expectation sets and 146 target trials
contain unloaded-arena environment errors. Unsupported command forms remain
visible. These results do not establish 96 current-source defects.

Raw command transcripts, packet bodies, copied scenarios and the report are in
`artifacts/jaron-lifecycle-catalog/20261016T021834.246879Z-6afa3c2a/`.
Both permanent services remained active afterward; this run used the released
RCON candidate, not a source-console substitute. Timed simulation cases live in
a separate catalog and were not part of this 96-case static run.

## Limits and preserved failures

The initial Pumpkin objective-list probe failed with `Incorrect argument for
command`; its raw responses and completed cleanup remain in
`artifacts/jaron-lifecycle-objective-unsupported.json`. No assertion about Pumpkin
scoreboard persistence follows from that command. A second audit exposed the
vanilla stop-status issue before its fix; that complete attempt is retained in
`artifacts/jaron-lifecycle-stop-status-red.json`.

Pumpkin preservation checks establish filesystem identity and marker survival.
Its released headless arena remains unloaded, so Pumpkin block persistence,
scoreboard persistence and shutdown durability of unsaved game state remain
untested. The vanilla sentinel was explicitly saved before restart. No claim of
power-loss durability, client gameplay, source-candidate RCON support or full
current-upstream parity is made. Rollback recovery failure remains an error.
