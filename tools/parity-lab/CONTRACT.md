# Pumpkin Parity Lab: implementation contract

## Goal

An actual differential testing lab comparing Minecraft Java 26.3 vanilla with
the official Pumpkin release supporting 26.3. Start with at least 20 deterministic
command-driven scenarios, then expand. This first phase does not claim to test
client gameplay, movement, inventories, or visual correctness unless actual clients
are implemented and exercised. Report command coverage separately.

Root: `/root/pumpkin-parity-lab`. Python 3.13 standard library preferred. Java 25
is installed. The initial release bootstrap needs no Rust build; subsequent
source-patch builds follow `ops/FORK.md`. Neither server nor RCON may bind publicly.

## File ownership during initial parallel implementation

- Christine worker: `lab/`, `tests/test_core*.py`, `pyproject.toml`.
- Jaron worker: `infra/`, `scenarios/`, `tests/test_scenarios*.py`, `docs/servers.md`.
- Coordinator: `ops/`, `web/`, root README/AGENTS/CONTRACT, dashboard and services.
- Do not edit another worker's files. You may read all project files. No git commits
  in the live lab repository while both workers are running. Fork worktree commits
  and pushes are authorized as specified in `ops/FORK.md`. Write a completion
  summary under `artifacts/`.

## Server lifecycle and target config

Jaron provisions official binaries with pinned versions and SHA-256/SHA-1 validation
from official manifests. Runtime directory `runtime/` (gitignored). Do not remove
unrelated caches. Server processes are resource-capped and restartable using systemd.
Vanilla game port 25575, RCON 25585; Pumpkin game 25576, RCON 25586.
Only bind 127.0.0.1. RCON password is randomly generated and stored mode 0600 in
`runtime/targets.json`; never log it or check it in. Keep useful server logs.

Targets file schema (shared interface):
```json
{"schema_version":1,"minecraft_version":"26.3","targets":{
  "vanilla":{"host":"127.0.0.1","port":25585,"password":"secret"},
  "pumpkin":{"host":"127.0.0.1","port":25586,"password":"secret"}
}}
```

## Scenario schema v1

One JSON file per scenario in `scenarios/`. IDs lowercase hyphenated, stable.
```json
{
 "schema_version":1,"id":"stone-placement","title":"Stone placement",
 "category":"blocks","description":"Explain what is being observed.",
 "tags":["command","deterministic"],
 "setup":["kill @e[type=!minecraft:player]","fill 0 60 0 8 70 8 minecraft:air"],
 "steps":[
   {"command":"setblock 2 64 2 minecraft:stone"},
   {"command":"execute if block 2 64 2 minecraft:stone run say PARITY:stone-present","observe":true,"expect_contains":"PARITY:stone-present"}
 ],
 "cleanup":["fill 0 60 0 8 70 8 minecraft:air"],
 "notes":"Known limitations and source of intended behavior."
}
```
Use only a bounded arena (x/z -32..32 y 48..96). No mass chunk generation.
Steps may have `wait_ticks` (integer, default 0) for simulation advances. Prefer
`tick freeze` + `tick step N` if both support it, otherwise classify unsupported;
do not turn capability gaps into parity passes. `command` is required for each step.
Observed steps are compared after narrow documented normalization of known server
prefixes only. Always preserve raw RCON responses. `expect_contains` is checked on
both targets, so two empty/failing responses cannot be a pass. Tests need at least
one observed step and an explicit positive observation expectation.

## Engine interface

- `python3 -m lab list [--scenarios scenarios]` emits catalog JSON.
- `python3 -m lab run --targets runtime/targets.json --scenarios scenarios --output artifacts/runs [--id SCENARIO_ID] [--repeat N]` runs both targets
  serially under a process file lock; creates a timestamped run directory with
  `report.json`, raw transcripts, and reproducible scenario copies. Print path.
  Exit 0 for all pass, 1 for detected differences/expectation failure, 2 for infra
  failure. Even partial/interrupted runs must not imply all tests passed.
- Report schema:
```json
{"schema_version":1,"run_id":"...","started_at":"ISO8601 UTC","finished_at":"ISO8601 UTC",
 "minecraft_version":"26.3","summary":{"passed":0,"different":0,"error":0,"total":0},
 "results":[{"id":"stone-placement","title":"...","category":"blocks","status":"pass|different|error",
 "observations":{"vanilla":["raw response"],"pumpkin":["raw response"]},
 "reason":"...","duration_seconds":0.1}]}
```
- Implement RCON TCP framing correctly, including fragmented responses, auth
  failure, and bounded read timeout; unit tests must cover actual fake-socket
  behavior rather than only normalizer output.
- `lab/shrink.py`: genuine delta debugging helper plus tests on a synthetic failing
  sequence. Never label a reproducer minimized without rerunning both servers.
- Flaky runs are visible and excluded from confirmed mismatch claims.
- Missing command, auth failure, malformed schema, server disconnection and
  unsupported features must remain visible, not silently skipped or passed.

## Initial validation

Engine worker can validate against fake RCON fixtures before servers exist. Server
worker must boot both actual servers and exercise RCON on both, independently of
the engine. Download Pumpkin source docs if necessary, never guess configuration
and then claim it worked. Prefer command-observable block and entity cases first;
each scenario tests a distinct behavior. Do not count renamed duplicate cases.

## Autonomous scope

Only these two assigned remote Codex processes, on GPT-6.1-Sol. Do not launch
additional agents, modify global Codex configuration, inspect other account files,
redeem resets, or use paid API providers. Do not claim success from code alone.
The user has additionally authorized autonomous Pumpkin fixes and pushes to their
fork. Follow ops/FORK.md for isolated worktrees, serial resource-capped builds,
and truthful validation records. Do not open upstream pull requests or issues.
Document actual commands run and actual results.
