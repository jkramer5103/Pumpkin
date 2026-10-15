# Genuine mismatch shrinking and replay

The lab CLI reduced the known execute positioned-anchor mismatch on current
upstream `5b53f064af8708ba33fcaa533b81ca29a53a3310` from seven to five steps.
Both observations, setup, cleanup and metadata stayed fixed. Every candidate ran
vanilla 26.3 over RCON and the immutable upstream binary through a fresh scratch
console, twice per target, under the shared engine file lock. Tagged arena
entities were reset before setup on every target and repeat. This validates
command-observable state, not current-source RCON or client gameplay.

The first session hit its 30-probe budget after saving the verified five-step
candidate, so its report correctly retains `minimized=false`. An interrupted
checkpoint session is also retained with no success claim. A separate completed
session reran the five-step candidate and all its possible unpinned single
deletions. It used 15 actual probes, including final verification.
The three unobserved dependency steps could not be removed while preserving the
original supported mismatch and vanilla's positive assertions. The result is
1-minimal with reset, setup, cleanup and observations fixed; it is not a claim
of global shortest length.

The exact saved replay command ran successfully and exited 1 for a stable
confirmed mismatch: the source-existence observation was `Test passed` on both
targets, and the feet-position observation was `Test passed` on vanilla and
`Test failed` on upstream, in both repeats. The same five-step case against the
already built positioned-anchor fix `f123eb8383eda4f6edbdcd71d840086901a4b339`
passed both observations twice on both targets. That underlying comparison
exited 0. The shrink CLI intentionally exited 2 for the fixed case because there
was no mismatch to minimize. No new Rust source change was needed for this task.

The CLI requires explicit reset and target-version files. It pins observations
and optional `--keep-step` indices, preserves exact divergent response identity,
checks local binary hashes before candidates and replay, and keeps raw evidence
and the best verified candidate even after an incomplete reduction. Existing
RCON service versions are declared provenance, not remote attestation. Console
selection is explicit and cannot silently turn absent RCON into a parity pass.
The console uses unique read-only scoreboard lookups for output framing; their
expected unknown-objective lines remain in full logs. Scratch processes stop
under the same engine lock used for their commands.

A reusable five-step case, reset commands and pinned version record are published
under `tools/parity-lab/lab/examples/`. From the live lab root, the actual replay
command is:

```sh
cd /root/pumpkin-parity-lab && /usr/bin/python3 -m lab replay --reproducer /root/pumpkin-parity-lab/artifacts/reproducers/shrink-qvjgtx1z --targets /root/pumpkin-parity-lab/runtime/targets.json
```

Original raw evidence remains on the lab host, outside Git:

- Original reduction: `artifacts/reproducers/shrink-cycj6i3z` (30 probes; budget exhausted).
- Verified minimality: `artifacts/reproducers/shrink-qvjgtx1z`; `campaign-original.json` preserves the seven-step original.
- Exact replay: `artifacts/reproducers/shrink-qvjgtx1z/replays/20261015T213935.483955Z-071589af`.
- Fixed comparison: `artifacts/reproducers/shrink-gmwv7tcu/runs/20261015T213949.363505Z-4a5da413`.
- Complete command/exit records: `artifacts/reproducers/anchor-validation.json`.

The verified reproducer session retains original/candidate cases, reset commands, target versions
and binary hashes, all attempts, run reports, raw RCON transcripts/packets, raw
console logs and an exact replay command. No worlds, binaries, target passwords
or runtime evidence are committed. The owned Python core suite passed 63 tests;
the final lab publisher independently passed 82 full-suite tests. Synthetic TCP
fixtures test shrinking, reset failures, pinned observations, budget exhaustion,
replay, wire fragmentation and refusal to substitute a different mismatch.
They are not counted as Minecraft parity cases. The previously validated Rust
fix and its build results remain documented in `christine-positioned-anchor.md`.
Full current-source RCON, player gameplay and performance remain untested.
