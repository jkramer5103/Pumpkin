# Minecraft Java 26.3 / protocol 777 client feasibility

Audit: 2026-10-16. An exact-version maintained client path **is feasible** through
MCProtocolLib's published 26.3 release. See [the implementation and commands](client-smoke/README.md).
No general gameplay coverage is claimed.

| Candidate checked | Pinned upstream evidence | Decision |
| --- | --- | --- |
| node-minecraft-protocol 1.68.0 | [supportedVersions at 1c83189](https://github.com/PrismarineJS/node-minecraft-protocol/blob/1c83189272348b9e12076465a748a5ecdd14acce/src/version.js) ends at 26.1 | No declared 26.3 client support |
| minecraft-data | [version table at 201ca80](https://github.com/PrismarineJS/minecraft-data/blob/201ca802a1b2c968b02e7fa5b31dd74e8bff3d8b/data/pc/common/protocolVersions.json) recognizes 26.3/777, but [dataPaths](https://github.com/PrismarineJS/minecraft-data/blob/201ca802a1b2c968b02e7fa5b31dd74e8bff3d8b/data/dataPaths.json) has no Java 26.3 protocol schema | A version number alone does not supply packet codecs |
| Mineflayer 4.39.0 | [tested versions at 7b4bb8d](https://github.com/PrismarineJS/mineflayer/blob/7b4bb8d2b56be9cdb832474af873acd37e609746/lib/version.js) ends at 26.1 | Not used for 777 gameplay |
| Azalea | [packet constants at 0d38e0d](https://github.com/azalea-rs/azalea/blob/0d38e0dcf47eb258c41b1b09ebc2bcde7253e185/azalea-protocol/src/packets/mod.rs) identify 26.2/776 | Not used; a protocol-number substitution is insufficient |
| MCProtocolLib | [codec at b4fa8b2](https://github.com/GeyserMC/MCProtocolLib/blob/b4fa8b23064bb85d7c7966cc2cd6bf369c9c1405/protocol/src/main/java/org/geysermc/mcprotocollib/protocol/codec/MinecraftCodec.java), [official release metadata](https://repo.opencollab.dev/main/org/geysermc/mcprotocollib/protocol/maven-metadata.xml), published `org.geysermc.mcprotocollib:protocol:26.3` | Selected; runtime version guard and artifact hashes required |

The published MCProtocolLib artifact is the tested dependency. It is not claimed
to be a build of the GitHub audit commit: its teleport-acceptance constructor
includes position/rotation fields absent from that checked source file. The
client follows the **published 26.3 codec**, with its jar SHA-256 locked locally.
This is why both artifact inspection and live vanilla validation matter.

The first live attempt is retained in
`artifacts/christine-client-scratch-20261016T061639Z/validation.json`: current
upstream Pumpkin reached play entry twice, but the vanilla scratch server rejected
the client because its default whitelist was enabled. Its initial status cache
also closed one request immediately after the startup log. Those are failed
setup attempts, not Pumpkin defects or passing two-server coverage. The final
scratch launcher explicitly disables the whitelist and records readiness probes
before measured trials. No existing scenario was changed or weakened.

Final bounded two-server validation passed, with two trials per target:
`artifacts/client-smoke-scratch/scratch-bc4ad2b8f006/validation.json` and
`runs/client-470a5a866e58/report.json`. Vanilla 26.3 and the current-upstream
Pumpkin baseline `5b53f064af8708ba33fcaa533b81ca29a53a3310` both passed exact
status/pong and all seven required login/configuration/play-entry events.
Both scratch processes stopped with exit 0. All startup, console setup, login
and shutdown held the shared engine process lock. No RCON was involved.

The ordinary authenticated lab services also passed two status/ping trials each:
`artifacts/client-status-live/client-5719f853e148/report.json`. Those services were
**not** used for offline login validation or reconfigured. Their Pumpkin binary
is the released candidate; the scratch login comparison above uses built upstream.

Validation commands actually run:

```sh
python3 lab/client-smoke/build.py
python3 -m unittest discover -s tests -p 'test_core*.py' -q
python3 -m lab.client_smoke --vanilla-port 25575 --pumpkin-port 25576 --repeat 2 --output artifacts/client-status-live
```

The scoped scratch command is recorded in the implementation README and actual
systemd invocation evidence. The owned Python suite passed 82 tests. The Java
client compiled against the pinned 79-jar graph and ran against both real servers.
These results establish **offline protocol entry**, not gameplay parity, online
account authentication or the absence of later packet/registry defects. No new
Pumpkin source defect is claimed from this smoke test; the previously validated
Christine execute-anchor source patch remains on the separate patch branch.

A final run of the provenance-complete implementation also passed all four trials:
`artifacts/client-smoke-scratch/scratch-9ef58129ebaf/validation.json` and
`runs/client-e8e80a9dfd3b/report.json` (see validation.json for the authoritative
inner path). Its report records and verifies the current Java source/class hashes.
The full shared test suite passed 119 tests before publication. Raw failed setup
and both successful runs are retained.
