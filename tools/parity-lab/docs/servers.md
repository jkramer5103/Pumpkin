# Private Minecraft 26.3 parity servers

This workspace runs the actual official Minecraft Java **26.3** server and official
Pumpkin **0.2.0+26.3-26.51**, downloaded as `pumpkin-X64-Linux`. Both advertise Java
protocol **777**, verified with a real server-list handshake. This section records
the initial released baseline. Source builds and subsequent validation are
recorded below and in `runtime/manifest.json` under `active_candidate`.

## Provision and operate

Run from `/root/pumpkin-parity-lab`, as root (systemd unit installation requires it):

```sh
python3 infra/provision.py
infra/servers status
infra/servers restart both
infra/servers stop pumpkin
infra/servers start pumpkin
infra/servers probe --command list
python3 infra/status_probe.py --output artifacts/game-status.json
infra/servers logs pumpkin
```

The provisioner downloads official metadata, verifies cached/downloaded binaries,
installs only the two named units, starts them, authenticates independently over
RCON, applies gamerules, and verifies their readback. Reprovisioning stops/restarts
these two services, preserves existing world directories and RCON passwords, and
regenerates managed server configuration. It never removes unrelated caches.
Lifecycle start/restart also reapplies controls and verifies RCON readiness.
Provisioning, lifecycle changes, and the independent scenario validator use the
same process lock as the engine to avoid changing worlds during a run.

Only explicitly requested flags change persistent identities/worlds:

```sh
python3 infra/provision.py --reset-worlds
python3 infra/provision.py --rotate-credentials
```

`--reset-worlds` archives each existing world beside its replacement with a UTC
suffix; server logs are retained. `--rotate-credentials` replaces both passwords.
Neither flag is used by normal start/restart. The Minecraft EULA is accepted in
`runtime/vanilla/eula.txt` for this user-authorized private setup.

| Service | Game address | RCON address | Limits |
| --- | --- | --- | --- |
| `pumpkin-parity-vanilla` | `127.0.0.1:25575` | `127.0.0.1:25585` | 3 GiB memory, no swap, 150% CPU, 128 tasks |
| `pumpkin-parity-pumpkin` | `127.0.0.1:25576` | `127.0.0.1:25586` | 3 GiB memory, no swap, 150% CPU, 128 tasks |

Vanilla's IPv6 socket display uses IPv4-mapped **127.0.0.1**, not a public wildcard.
RCON and game bindings were checked with `ss`. Bedrock, query, LAN broadcast,
Pumpkin plugins, and Pumpkin telemetry are disabled. Online authentication remains
enabled; these tests need no player account or game client. Units use a read-only
system filesystem with write access restricted to their own runtime directory,
no capabilities, and `NoNewPrivileges`. The JVM heap is capped at 2 GiB.

`runtime/targets.json` follows CONTRACT schema v1 and is mode **0600**. Passwords
are randomly generated, read from that file, and never passed in process arguments
or printed. Server config files necessarily contain their matching passwords and
are also private. `runtime/` and `artifacts/` are gitignored. Do not copy complete
server configuration or targets into reports. Pumpkin command/password-failure
logging is disabled. Bootstrap evidence and manifests contain no credentials.

## Official provenance

`runtime/manifest.json` records versions, source/download URLs, SHA-1 and SHA-256
of both binaries, release publication time, tag commit, source archive SHA-256,
ports, resource limits, and requested gamerules. Upstream JSON snapshots are in
`runtime/upstream/`; binaries and checksum file are in `runtime/downloads/`.

The release was verified against the current official latest-release endpoint.
The provisioner fails if latest changes away from the reviewed pin. Mojang's
version metadata is SHA-1 checked against the version manifest, then the server
JAR is SHA-1 checked against that metadata. Pumpkin's SHA-256 is checked against
**both** its published checksum file and GitHub asset digest; the checksum file
itself is checked against its GitHub digest. Source archive hashes are locally
computed provenance, not publisher signatures.

| Artifact | Verified digest |
| --- | --- |
| Minecraft server SHA-1 | `33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c` |
| Minecraft server SHA-256 | `d052f14d7a173734fba553711e5b570162e2f2a313267ee31a21b975a679be64` |
| Pumpkin binary SHA-256 | `68c4416ca9fbfb3f2aeb6a8ce1de0e3fb02c5a85a53c8ba59a27941d7e43d8cd` |
| Pumpkin checksum file SHA-256 | `4d8f7268a3bb401b565c5c48d36b10a88d5bb22c51c9a32209236e790395b9ee` |
| Pumpkin tagged source commit | `204a94ed895f041a845630d5a23c094705a0704e` |

Sources: [Mojang version manifest](https://piston-meta.mojang.com/mc/game/version_manifest_v2.json),
[Mojang 26.3 metadata](https://piston-meta.mojang.com/v1/packages/11f1aefe473eefba0af62e3286c33b692807b2eb/26.3.json),
[Pumpkin release](https://github.com/Pumpkin-MC/Pumpkin/releases/tag/0.2.0%2B26.3-26.51),
[latest release API](https://api.github.com/repos/Pumpkin-MC/Pumpkin/releases/latest),
[configuration docs](https://docs.pumpkinmc.org/config/basic), and
[RCON docs](https://docs.pumpkinmc.org/config/rcon).

## Flat worlds and controls

Vanilla uses its official flat generator, seed `123456789`, structures disabled,
with bedrock, two dirt layers, and grass at the bottom of the world. Tests operate
in the empty arena above it, x/z within -32..32 and y within 48..96. The authored
block mutations use x/z 0..8 and y 60..75. Worlds have independent storage; no
region/chunk files or entity data are shared.

A material upstream limitation was observed: this Pumpkin release advertises
26.3 but rejects vanilla 26.3's `DataVersion 5023` level metadata. Its tagged
source explicitly caps accepted world metadata at **4903**. Consequently
`infra/flat_world.py` seeds a **new**, empty Pumpkin world using its own supported
metadata version, with a flat generator in
`data/minecraft/world_gen_settings.dat`. It refuses to overwrite existing
`level.dat`. This is initialization of fresh metadata; no existing world is
converted. The initial rejected bootstrap metadata is preserved under
`runtime/pumpkin/world.failed-bootstrap`, and its startup logs are retained.

This behavior was established from the tagged source's
[`world_info` constants](https://github.com/Pumpkin-MC/Pumpkin/blob/204a94ed895f041a845630d5a23c094705a0704e/crates/pumpkin-world/src/world_info/mod.rs),
[world-info reader](https://github.com/Pumpkin-MC/Pumpkin/blob/204a94ed895f041a845630d5a23c094705a0704e/crates/pumpkin-world/src/world_info/anvil.rs),
[split data-file reader](https://github.com/Pumpkin-MC/Pumpkin/blob/204a94ed895f041a845630d5a23c094705a0704e/crates/pumpkin-world/src/world_info/data_files.rs),
and [generator selection](https://github.com/Pumpkin-MC/Pumpkin/blob/204a94ed895f041a845630d5a23c094705a0704e/crates/pumpkin-world/src/level.rs).
Generated Pumpkin defaults were inspected after boot with Python `tomllib`.
TOML root keys precede every table; `[networking.java]` and `[networking.rcon]`
contain the actual bind addresses. There is no invented TOML `flat` setting.

Both servers verify these gamerules via RCON readback:

```text
advance_time=false       advance_weather=false
spawn_mobs=false         random_tick_speed=0
mob_griefing=false       block_drops=false
entity_drops=false       send_command_feedback=true
log_admin_commands=false
```

Time is set to 6000, weather to clear, spawn to the flat surface, and the bounded
arena is marked for force loading. These controls are recorded in
`runtime/vanilla-bootstrap.json` and `runtime/pumpkin-bootstrap.json` with raw
responses. The bare snake_case gamerule names work on both; Pumpkin rejects the
`minecraft:` prefix accepted by vanilla.

**Pumpkin chunk readiness remains unsupported in this headless setup.** Its
`forceload add` reports success but only updates the active set; the tagged source
does not fetch missing chunks there. Subsequent `setblock` and `fill` report
`That position is not loaded`. Even a bounded investigation using its embedded
`pumpkin:summon_command_regression` GameTest did not make the arena writable; the
GameTest was stopped. No chunk-loading client was implemented. The flat metadata
is verified, but actual generated Pumpkin terrain and block semantics beyond this
loading failure are **untested**. A successful force-load command is not recorded
as proof that the chunks loaded.

## Scenarios and live evidence

There are **50 distinct schema-v1 scenarios**, one JSON file each. They cover:

- Placement, replacement, occupied/empty keep behavior, state replacement,
  log axis, stair orientation, and waterlogged slabs.
- Bounded solid, hollow, outline, keep, material-filtered, and state-filtered fills.
- Replace, masked, filtered, move, and overlapping forced clones.
- Partial-state, tag, tag-with-state and negative block predicates; reversed fill
  endpoints, tag/state fill filters, state-filtered clones, masked moves and
  overlap rejection. Container placement, replacement and cloning observe real
  stored item stacks; replacement proves the stack existed before clearing it.
- Relative execution origin; signed scoreboard add/remove, multiplication,
  floor division, modulo, assignment, swap, minimum/maximum, and selector counting.
- Tag addition/removal/intersection, selective kill, marker nested NBT,
  NBT merge/list append, and integer-coordinate teleport centering.

Every observation has a positive `expect_contains` and reads gameplay state with
an `execute if/unless` predicate. Error messages, matching empty replies, and
command acceptance cannot pass these checks. The occupied `keep` case deliberately
attempts a failing mutation in setup and then positively observes the original
block's preservation. Entity selectors are restricted to tagged markers inside
the bounded arena. Random UUID/display-name outputs are not observations.

The independent baseline validator imports **no lab engine code**:

```sh
python3 infra/validate_scenarios.py --target vanilla --repeat 2 --output artifacts/vanilla-baseline.json
python3 infra/validate_scenarios.py --target pumpkin --repeat 2 --output artifacts/pumpkin-baseline.json
python3 -m unittest discover -s tests -p 'test_scenarios*.py' -v
```

Initial result: vanilla **74/74** positive scenario expectation sets satisfied
(37 scenarios × 2); Pumpkin **0/74**. All raw setup/step/cleanup replies are in
those artifacts. Pumpkin failures include unloaded chunks, unsupported terminal
execute predicates, fake-player scoreboard arguments, and entity NBT/selector
command forms. These are visible capability/expectation failures, not 37 confirmed
underlying gameplay bugs. Vanilla checks also established that integer teleport
x/z coordinates center entities at `.5`; the scenario observes that actual state.
`time query daytime` is not valid 26.3 timeline syntax, and `say` provides no useful
vanilla RCON observation, so neither is used as a state-success oracle.

`infra/rcon_probe.py` independently implements framing/authentication, exact reads,
and a subsequent `list` completion fence. It waits for the first response before
sending the fence because vanilla rejects the coalesced command form used in the
initial engine. Its unit test uses a real local fake server with byte-fragmented
frames and a multi-frame command response.

An actual engine subset was attempted:

```sh
python3 -m lab run --targets runtime/targets.json --scenarios scenarios --output artifacts/runs --id stone-placement --repeat 2
```

The initial run is preserved at
`artifacts/runs/20261015T204803.409413Z-ab3dc416/`: exit **2**, RCON disconnection /
response-boundary infrastructure errors. It is **not** a parity pass or confirmed
block mismatch. No `lab/` files were changed. Engine transport fixes and follow-up
engine runs belong to the concurrent engine worker. A second attempted subset, `score-add-remove --repeat 2`, also exited 2 and is preserved at `artifacts/runs/20261015T205446.178407Z-8229b64e/`.

Additional evidence: `artifacts/game-status.json`,
`artifacts/independent-rcon-smoke.json`, `artifacts/provision-repeatability.json`,
and `runtime/manifest.json`. Server stdout/stderr append to each
`runtime/<target>/service.log`; native server logs remain under their runtime
folders. Reprovisioning was exercised with unchanged credentials, preserved world
directory identity/marker files, and a vanilla diamond-block state surviving the
restart. The probe block and marker files were removed afterward.

Each scenario freezes simulation in setup and unfreezes it in cleanup; both tick commands were exercised on both servers. These are immediate command-state scenarios, not simulation timing tests. Client
login/gameplay, movement physics, inventories, combat, visual behavior, elapsed
tick behavior, and Pumpkin generated-terrain equivalence remain untested. No
scenario claims a tick advance from wall-clock sleep.

## Expanded catalog review

All original 37 cases were rerun on live vanilla before expansion. All 50 cases
then met their positive expectations twice: **100/100** scenario expectation sets
in `artifacts/jaron-catalog50-vanilla.json`. The released Pumpkin candidate met
**0/50** in `artifacts/jaron-release-catalog50.json`. These are capability/state
expectation results, not a count of independent gameplay defects. The bounded
engine attempt exited **2** with candidate environment errors, preserved at
`artifacts/runs/20261015T210048.698585Z-0275a6be`. This engine invocation ultimately
selected only `block-entity-nbt-placement`, because `--id` is a single-value flag.

The independent validator now snapshots scenario definitions and writes raw
responses atomically after each command. An interrupted scenario starts with
`complete=false` and `expectations_met=false`; no partial run can imply success.
The direct RCON CLI also takes the engine lock, including arbitrary mutating
`--command` probes. It remains independent of `lab/`.

Source builds use the Jaron worktree, the shared cargo target/build lock, one
build job, no incremental compilation or debug info, and a systemd scope capped
at 5 GiB memory, zero swap and 200% CPU. Source candidate installation is:

```sh
python3 infra/deploy_candidate.py --binary /root/pumpkin-parity-worktrees/target/debug/pumpkin --build-command 'the exact completed build command'
```

The installer holds the engine lock, backs up the manifest/config/service
override privately, copies and hashes the binary, and restarts only the candidate.
Its manifest entry records source commit, binary hash and exact build command.
Readiness verifies RCON and controlled gamerules; it does not claim block readiness.
Existing source-candidate provenance survives normal reprovisioning. The released
binary and old logs/worlds remain available. See [integration notes](jaron-integration.md)
and `artifacts/jaron-fork-status.json` for current source validation and limitations.

The clean current-upstream build at `5b53f064` completed in **9m39s** and booted
successfully. This revision contains **no RCON implementation/configuration**;
the candidate listened on game port 25576 but never on RCON 25586. Readiness and
the source-baseline comparison could not complete. The released binary and
private configuration were restored under the engine lock, and RCON/gamerules
were verified again. The exact source/hash/build/deployment attempt is retained
in `runtime/manifest.json.source_baseline_attempts` and
`artifacts/jaron-upstream-deployment.json`. No source-baseline parity pass or
50-case source-baseline failure is claimed. The partial artifact
`artifacts/jaron-upstream-catalog50.json` contains zero completed results.

## Current-source fill fix

`701809df211b0dcfa6996595f99ff7327cad8d78` changes fill filters to compare supplied
properties against each actual block state, for both named blocks and tags.
Unspecified properties remain unconstrained; block-entity NBT filtering remains
a separate gap. The regression failed with original current-upstream matching,
then all **81 command unit tests and 5 doc tests** passed after the fix. Workspace
formatting, command-crate clippy and the full patched binary build passed.

Because current upstream has no RCON, a separate bounded console comparison held
the engine lock and used resource-capped scratch servers. A private one-block
loader fixture made one chunk writable after the embedded fixture failed its
palette schema. Original failed attempts are retained. Named and tag filters
were each exercised twice with positive initial-state, negative branch,
nonmatching preservation and matching replacement controls. Vanilla and patched
code passed all checks; clean upstream failed preservation in all four attempts.
This confirms one state-filter defect and its fix, without claiming full catalog
parity or a passing GameTest. Raw logs/report are in
`artifacts/jaron-fill-console-20261015T212702.924070Z/`. The released RCON candidate
remains active; no patched deployment or real-client visual test is claimed.
