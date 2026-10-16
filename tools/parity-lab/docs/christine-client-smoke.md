# Exact Minecraft 26.3 / protocol 777 client smoke

A maintained exact-version client path is available: the published
`org.geysermc.mcprotocollib:protocol:26.3` artifact. Its runtime codec is checked
for Minecraft 26.3 and protocol 777 before connecting; the full 79-jar dependency
graph is SHA-256 locked. Mineflayer/node-minecraft-protocol declare support only
through 26.1 in the inspected revisions, and Azalea targets 26.2/776. Merely
recognizing 777 in minecraft-data's version table does not supply a 26.3 codec.
Pinned source links and the implementation are published separately on the
[`parity-lab` campaign branch](https://github.com/jkramer5103/Pumpkin/tree/parity-lab/tools/parity-lab/lab/client-smoke).
No new Pumpkin source defect is claimed from this test.

The lab now has a Python status/ping probe, a Java login smoke client, a
serial two-target comparison harness, and an optional isolated scratch-server
launcher. These use game TCP sockets, never RCON. All startup, spawn setup,
client connections and shutdown hold the engine's shared process lock.
Existing authenticated lab services/configuration/worlds remain unchanged.

The Java client requires decoded login success, configuration completion, play
login and initial position, plus transmitted login/configuration/teleport
acknowledgments. It then stays connected for two seconds. The published 26.3
teleport acknowledgment includes coordinates and rotation; the client does not
substitute an older codec. Relative initial positions are explicitly unsupported.
Raw status/pong bytes, packet event types, logs, binary hashes and failure evidence
remain in local artifacts. This is offline protocol entry only: movement,
inventories, block interaction, online authentication and rendering are untested.

## Actual validation

- `python3 lab/client-smoke/build.py`: Maven dependency resolution, hash verification
  and `javac` succeeded. Tools, downloaded jars and classes are isolated in
  `runtime/client-smoke/`; no global installation or Python dependency was added.
- `python3 -m unittest discover -s tests -p 'test_core*.py' -q`: 82 passed, including
  actual TCP fixtures for fragmented status packets, malformed VarInts, oversized
  lengths, truncation, wrong pong, a total deadline, exact-version mismatch and
  preservation of a two-target failure. These fixtures do not claim real login.
- `python3 -m unittest discover -s tests -q`: 119 passed in the shared lab.
- Authenticated live services: two actual status/pong trials per server passed at
  `artifacts/client-status-live/client-5719f853e148/report.json`. Their released
  candidate was used for status only.
- Current-upstream comparison: vanilla 26.3 versus built upstream
  `5b53f064af8708ba33fcaa533b81ca29a53a3310`, two trials each. All four actual
  status/pong and login/configuration/play-entry smoke trials passed. Both scratch
  servers stopped with exit 0. Evidence:
  `artifacts/client-smoke-scratch/scratch-bc4ad2b8f006/validation.json`, inner report
  `runs/client-470a5a866e58/report.json`.
- Upstream master was independently rechecked with `git ls-remote upstream
  refs/heads/master`, returning that same revision. No rebuild was necessary:
  the already-built baseline SHA-256 remains
  `463905ffe45d2dd55d1cf6511bdd7548fd21ef8977125bfe57b7a2ea55350eb7`.
- Actual scope: `pumpkin-parity-christine-client-final.service`, `MemoryMax=3G`,
  `MemorySwapMax=0`, `CPUQuota=200%`, `TasksMax=128`, outer timeout 240 seconds.
  No Cargo operations or upstream PRs/issues were performed.

The initial unsuccessful setup is preserved at
`artifacts/christine-client-scratch-20261016T061639Z/validation.json`: vanilla
rejected the client because its default whitelist was enabled; one first status
request also preceded its status cache readiness. The scratch launcher now
explicitly disables the whitelist and records bootstrap status probes separately
from measured trials. No scenario or assertion was removed or weakened.

Known Java native-access/Unsafe warnings, the explicit offline-server warning,
and Pumpkin's development/debug-build warnings are retained. The final smoke
server/client logs have no ERROR/panic/exception matches. These bounded results
do not establish broad gameplay parity or performance, and do not validate the
existing execute-anchor source fix through a client.
