# Evidence integrity and recovery

The engine fixes are published on the authorized `parity-lab` branch in
`21b414e44aba451f749ee2fdca2d5d742f14936f`. This document records tooling work;
there is no new Pumpkin gameplay patch in this assignment. The existing
execute-anchor fix is `f123eb8383eda4f6edbdcd71d840086901a4b339`.

## Actual fixes

- A report now checkpoints requests, responses, observations and target completion.
  Lost replies remain uncertain even after a successful cleanup. Interruptions
  retain partially received wire bytes and response fragments in raw transcripts.
- `lab recover --run DIRECTORY` locks the engine, verifies that the original
  PID/start-time/boot identity is no longer alive, and marks abandoned evidence
  incomplete. Original transcript bytes, including torn lines, remain untouched.
  Recovery does not replay commands, reconnect, or assert cleanup/tick restoration.
- Cleanup after a scratch-console disconnect no longer tries to recreate the
  existing directory and abort the rest of the suite. It reports the unavailable
  cleanup session while continuing the remaining targets and trials.
- Scenario snapshots are saved before waiting for the shared lock, so a lock
  timeout retains the exact requested catalog inputs.
- Ordinary runs accept explicit allowlisted version metadata and record hashes
  plus optional local world-directory device/inode identities. These are checked
  after the lock wait and before each target. Current-source scratch binaries are
  always hashed and attempts record their world directory identity when present.
- Shrink/fuzz propagate their versions into individual run reports. Replay rejects
  edited version metadata; new shrink sessions also hash the verified scenario,
  reset and saved replay policy and reject modified inputs before connecting.

## Validation

`python3 -m unittest discover -s tests -q` passes all 128 tests. The authorized
publisher independently reran and passed those 128 tests before pushing. Nine
integrity tests exercise actual SIGKILL of a TCP fixture runner, lock contention,
atomic-write failure, scratch subprocess disconnects, interrupted wire evidence,
world replacement, binary replacement during a lock wait, and modified replay
inputs. Four selected regressions fail against the preserved original runner and
CLI; the corrected before-patch log is
`artifacts/christine-integrity-regressions-before-final.log`.

The current catalog has 100 validated scenario definitions. The first bounded
live RCON run reached its 180-second limit after 48 completed scenario attempts;
its interrupted report and raw transcripts remain unchanged at
`artifacts/integrity-catalog/20261016T062949.099708Z-5d20faec/report.json`.
Follow-up validation runs only the remaining cases with full setup/cleanup again.
No partial command is retried automatically.

The follow-up completed all 52 remaining scenarios. Combined coverage is exactly
100 current scenario definitions, one completed trial each: 76 infrastructure
errors and 24 differences/capability failures, with zero failing vanilla positive
assertions. This is failure evidence against the older released RCON candidate,
not 100 parity passes or new current-source defects. Single trials establish no
confirmed mismatch claims.

Current upstream master was verified using
`git ls-remote upstream refs/heads/master`:
`5b53f064af8708ba33fcaa533b81ca29a53a3310`. Existing immutable current-source and
fixed binaries are reused; no Cargo operation or rebuild was needed. The bounded
live follow-up runs under `pumpkin-parity-christine-integrity-live.scope` with
`MemoryMax=3G`, `MemorySwapMax=0`, `CPUQuota=200%`, `TasksMax=128` and a 540-second
outer timeout. Every server-mutating comparison and scratch shutdown uses the
engine's shared process lock.

Final live results are recorded in
`artifacts/christine-integrity-live-validation.json` and the final validation
record referenced by `artifacts/christine-fork-status.json`.

The bounded current-source suite completed two trials per scenario on both
targets: upstream reproduces the known anchor mismatch in both trials and passes
score arithmetic; the existing `f123eb8` fix passes both scenarios in both trials.
No flakes or infrastructure errors occurred. Freeze/step probes verify one actual
game-time tick and restore running state. Reports retain declared source commits,
binary hashes, and all scratch-world device/inode identities:

- Upstream: `artifacts/integrity-upstream/20261016T063656.879723Z-4d1ddc44/report.json`
- Fixed: `artifacts/integrity-fixed/20261016T063746.397733Z-b60d0265/report.json`

The final audit finds all 100 current catalog snapshots match, reconstructs 1,972
raw RCON responses exactly from their recorded response packet fragments, and
finds normal stop messages with no ERROR/panic matches in all ten source scratch
logs. Evidence: `artifacts/christine-integrity-final-audit.json`. The capped live
scope exited 0; the released-catalog comparisons exit 2 for their actual failures.

## Limits and coordinator integration

`ops/supervisor.py` was read without modification. Integration findings are in
the local `artifacts/engine-integration-notes.md`: dead-owner run recovery is not
yet called by the supervisor; completed model turns do not themselves establish
validation success; operational callers must retain the same TMPDIR/UID for the
existing engine lock; coordinator JSON writes use a fixed temporary filename and
lack the engine's fsync guarantees. These coordinator-owned changes are notes,
not implemented fixes.

World device/inode is local directory identity, not a content snapshot or proof
of a seed, loaded RCON world, or server process identity. General replay
determinism and arbitrary state restoration remain unproven. Legacy reproducers
do not have the new scenario/reset/policy hashes, and legacy run reports without
owner identity cannot be automatically recovered safely. Recovery cannot prove
world/tick cleanup. Current upstream has no RCON implementation; full catalog
RCON evidence identifies the older released candidate, while current-source
comparisons explicitly use scratch console. No tests were removed or weakened.
