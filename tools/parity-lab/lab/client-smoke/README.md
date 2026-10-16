# Exact 26.3 client smoke

This optional Java client uses the maintained **MCProtocolLib 26.3** release,
whose runtime codec must report Minecraft `26.3` and protocol `777` before
connecting. Python's command-testing engine keeps its standard-library-only
installation. No Python package, account token, Microsoft login or paid service
is needed. No RCON connection is made by either client probe.

The Java probe completes offline login, acknowledges login/configuration, decodes
play login and the initial absolute position, sends the 26.3 teleport acceptance
(including coordinates/rotation), and remains connected for two seconds. All seven
required packet events must occur. Decode failures, early disconnects, relative
initial positions, event overflow and process timeouts cannot pass. The client
records packet types and initial position, not raw binary gameplay traffic.

This establishes protocol entry only. Movement, inventory operations, block
interaction, chat, online authentication, visual correctness and performance are
**untested**. Chunk packets may be decoded during the observation interval; that
does not establish chunk rendering or gameplay correctness. Spawn positions in
independent worlds are recorded without asserting that they match.

## Isolated dependencies and build

Java 25, `javac` and Python 3.13 are used in this lab. Maven 3.9.11 is bootstrapped
from Maven Central with a pinned SHA-512. The exact 79-jar transitive classpath
(including MCProtocolLib) is SHA-256 locked in `dependencies.sha256.json`.
`build.py` rejects changed artifacts/graphs before compilation. The Maven plugin
is pinned in the build command. Downloaded tools, dependency cache, classpath and
compiled classes stay in `runtime/client-smoke/`, outside the published sources.
No system Maven installation or global dependency cache is changed.

```sh
python3 lab/client-smoke/build.py
```

For a constrained remote machine, run that build in a scope with
`MemoryMax=1G`, `MemorySwapMax=0`, `CPUQuota=100%`. It performs no Cargo operation.
Dependency repositories are Maven Central and MCProtocolLib's official
`https://repo.opencollab.dev/main/` endpoint. The `/maven-releases/` artifact URL
returned HTTP 403 here; the documented `/main/` endpoint successfully resolved
the exact release. There is no fallback to an older Minecraft codec.

## Bounded two-server smoke

The reusable scratch entry point creates independent flat worlds, disables
whitelists/authentication **only in those scratch servers**, binds game sockets
to `127.0.0.1` on allocated ports, and disables RCON. Existing services/worlds
are untouched. Two-chunk view/simulation distances and two client repeats keep
the run small. Startup status readiness probes are recorded separately; measured
trials do not retry failures. Servers stop in `finally`, while the shared engine
lock is still held. An occupied allocated port causes a visible startup failure.

Run with already-provisioned lab binaries (replace the Pumpkin revision/path
when a newer baseline is built):

```sh
systemd-run --scope --unit=pumpkin-parity-client-smoke \
  -p MemoryMax=3G -p MemorySwapMax=0 -p CPUQuota=200% -p TasksMax=128 \
  /usr/bin/timeout 240 python3 -m lab.client_smoke_scratch \
  --vanilla-jar runtime/downloads/minecraft-26.3.jar \
  --pumpkin-binary runtime/downloads/pumpkin-source-5b53f064af8708ba33fcaa533b81ca29a53a3310 \
  --pumpkin-source 5b53f064af8708ba33fcaa533b81ca29a53a3310 --repeat 2
```

The outer validation JSON contains binary hashes, commands, declared source,
readiness and shutdown evidence. A source name is declared provenance; it is not
inferred from the status string. The inner `report.json` contains each status
request/response as hex, original JSON, pong identity and latency, login packet
events, dependency hashes and client source/class hashes. Client stderr and both
server consoles remain beside the report. Exit 0 requires both targets to pass
all trials and both scratch processes to stop normally. Exit 2 means a failure
or incomplete run, never a confirmed gameplay-parity mismatch.

For two independently managed **offline scratch** endpoints:

```sh
python3 -m lab.client_smoke --vanilla-port 25577 --pumpkin-port 25578 \
  --classpath-file runtime/client-smoke/classpath.txt --repeat 2
```

The engine process lock covers every comparison. Lifecycle changes by an
external launcher must hold the same lock, so the bundled scratch entry point is
preferred. Omitting `--classpath-file` runs **status/ping only** and reports
`login_tested=false`; it never implies successful login:

```sh
python3 -m lab.client_smoke --vanilla-port 25575 --pumpkin-port 25576 --repeat 2
```

Status uses a real Java handshake with protocol 777 and status next-state, then
checks the returned version and exact eight-byte pong payload. Packet size,
VarInt length, partial reads and total deadline are bounded. Raw partial evidence
is retained on failure. MOTD, favicon, player count and latency are not equalized
or treated as gameplay assertions.
