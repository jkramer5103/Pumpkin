"""Create a finite, reviewable campaign. Never generates an endless token loop."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = """
Read AGENTS.md, CONTRACT.md and ops/FORK.md before work. The user explicitly
authorized YOLO mode and autonomous fixes pushed to jkramer5103/Pumpkin.
Remain on gpt-6.1-sol with this isolated subscription. No extra agents, paid API
providers, banked reset redemptions, upstream PRs or unrelated server changes.
Use your isolated Pumpkin worktree and push your own branch per ops/FORK.md.
Do not commit the shared live lab repository while the other lane runs.
Prioritize actual fixes over growing counts. Reproduce on current upstream:
the released Pumpkin binary predates master and known gaps may already be fixed.
If you have not yet produced a source patch, actively investigate a real failure
in your assigned subsystem and patch/test/push it if feasible. For the Jaron lane,
building and deploying current upstream baseline is the first priority after
initial provisioning. For Christine, investigate execute/scoreboard/RCON parity
on current upstream while the baseline builds. Serialize resource-capped builds.
Record all actual pushes and validation in artifacts/<account>-fork-status.json.
After meaningful validated lab changes, run python3 ops/publish-lab.py to snapshot
them to the authorized parity-lab branch. It serializes pushes and excludes
runtime secrets/artifacts. Pumpkin source patches go on your own patch branch.
Do not remove or weaken tests merely because Pumpkin fails them. Preserve
actual server evidence. Report unsupported and untested behavior honestly.
Run the applicable unit tests and a bounded live comparison if possible.
All server-mutating comparisons must hold the engine's shared file lock.
If another lane owns a file, write an integration note instead of editing it.
Finish with a concise account of actual changes, commands and results.
"""

TASKS = {
"christine": [
 ("Live integration and verdict correctness", """You own lab/, tests/test_core*.py, pyproject.toml.
Inspect initial engine, actual server configurations, generated scenarios and
latest reports. Fix practical integration defects in your files. Verify the
entire current scenario catalog against both servers. Check that mismatches,
unsupported commands and failed positive assertions are correctly distinguished
from connection/infrastructure failures. Add focused regression tests for real
failures. Avoid broad response normalization that masks real differences."""),
 ("Real mismatch reduction and replay", """You own lab/, tests/test_core*.py, pyproject.toml.
Implement a usable shrink CLI for actual mismatching scenarios. Re-run both
servers for every candidate, reset arena before each, preserve required setup
and observation steps, and never claim minimality without actual checks. Save
original, reduced candidate, attempts, target versions, raw evidence and an exact
replay command under artifacts/reproducers/. Validate against a genuine current
mismatch if any exists; otherwise explicitly label synthetic demonstrations."""),
 ("Repeated trials and deterministic simulation", """You own lab/, tests/test_core*.py, pyproject.toml.
Strengthen repeated-trial handling and test-order isolation. Identify actual
differences that reproduce twice and separate flaky/non-deterministic cases.
Probe tick-freeze/step support on both servers, with honest capability status.
Add targeted tests and runtime report details. Keep existing report keys used
by ops/dashboard.py compatible, adding fields rather than changing them."""),
 ("Seeded differential fuzzing", """You own lab/, tests/test_core*.py, pyproject.toml.
Add a bounded, reproducible fuzz CLI for safe scoreboard arithmetic and bounded
block operations. Persist seed, generated actions and failures; run the same
sequence against both servers; reduce reproducible failures through the existing
reducer. Add strict action/time/arena limits and positive observations. Run at
least ten meaningful seeds live and summarize actual findings. No infinite fuzzing."""),
 ("Protocol and client test feasibility", """You own lab/, tests/test_core*.py, pyproject.toml.
Investigate an actual client path for exact Minecraft 26.3/protocol 777. Prefer
a maintained client library only if it supports that exact version. Implement
a real two-server login/status smoke harness if feasible and validate it. Never
fake a client with only RCON. If unsupported, write lab/client-feasibility.md with
precise upstream blockers and a tested status-ping probe; do not pretend gameplay
is covered. Keep new dependencies isolated and documented within lab/."""),
 ("Evidence integrity and unattended recovery", """You own lab/, tests/test_core*.py, pyproject.toml.
Audit atomic report writes, interrupted runs, lock contention, disconnects,
world identity, target version recording and replay determinism. Improve actual
weaknesses and add meaningful regressions. Read ops/supervisor.py without editing
it; report any integration defect under artifacts/engine-integration-notes.md.
Validate the catalog as it currently exists, even if it grew since earlier jobs."""),
 ("Final campaign verification", """You own lab/, tests/test_core*.py, pyproject.toml.
Run complete unit tests and current live catalog with repeat=2. Investigate a
representative confirmed mismatch and preserve a minimal reproduction if possible.
Fix engine defects in your scope. Write artifacts/engine-final-audit.md with
actual coverage, confirmed findings, limitations, and next concrete tasks. Finish
this finite campaign; do not create new work just to consume quota."""),
],
"jaron": [
 ("Validate and expand the initial catalog", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/servers.md,
and other docs/ findings. Review initial provision and every existing scenario
against live vanilla. Correct invalid vanilla commands, do not weaken candidate
failures. Expand toward 50 distinct behaviors. Focus on block states, replacement,
fill filters, clone operations and block predicates. Each observed probe must
prove the intended behavior via a positive sentinel or meaningful structured state.
Do not count simple renamed block IDs as separate mechanic coverage."""),
 ("Entities and selectors coverage", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/.
Add up to 25 distinct meaningful deterministic entity scenarios: summon, tags,
selector predicates/counts, NBT fields, effects where entity-observable, entity
cleanup, and positions. Validate each against live vanilla 26.3. Preserve raw
candidate failures as real findings. Respect shared arena and runner lock.
Do not claim player inventory or combat tests without an actual connected player."""),
 ("Execution and scoreboard semantics", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/.
Add up to 25 distinct execute/scoreboard behavior tests, including boundary
arithmetic, comparisons, condition chains, target selection and state changes.
Validate reference results live and retain explicit observations; don't pad with
equivalent renamed cases. Add schema checks for catalog duplicates and required
positive probes. Read engine code for supported step fields before writing them."""),
 ("Simulation-dependent block behavior", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/.
Probe tick control capabilities honestly. Add meaningful deterministic physics,
growth, fluid, scheduled-block or redstone checks only where both engines can
be advanced reproducibly. Add prerequisite metadata if the engine supports it;
otherwise document blocked checks rather than pretend they passed. Validate
actual vanilla behavior and avoid arbitrary sleep-based flaky assertions."""),
 ("Server lifecycle and reproducibility audit", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/.
Make provisioning and lifecycle commands idempotent, preserve world data and
credentials, pin artifacts with checksums and inspect localhost-only listeners.
Coordinate disruptive test-server restarts using the engine's same process lock.
Test stop/start recovery and document exact commands. Never restart unrelated
services. Run a bounded full catalog after both servers recover."""),
 ("Investigate confirmed Pumpkin differences", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/.
Review real comparison results and investigate the top five reproducible
behavior differences. Reproduce twice, inspect upstream Pumpkin source and
existing issues for overlap using read-only tools, and write docs/findings.md
with expected/actual behavior, source pointers and replay commands. Do not file
issues or PRs. Do not call invalid reference scenarios Pumpkin bugs. No Rust builds."""),
 ("Final catalog audit and coverage map", """You own infra/, scenarios/, tests/test_scenarios*.py, docs/.
Review catalog quality and coverage, remove genuine duplicates only with clear
reason, fix invalid probes and fill valuable gaps. Prefer 100+ genuinely distinct
checks if feasible; never pad counts. Write docs/coverage.md distinguishing
command behavior, actual gameplay, protocol tests, missing tests and known
flakiness. Run schema checks and a live repeated catalog if available. Finish
the finite campaign; do not create new work merely to consume quota."""),
]}

for account, tasks in TASKS.items():
    directory = ROOT / "ops" / "tasks" / account
    directory.mkdir(parents=True, exist_ok=True)
    initial = (ROOT / "ops" / f"{account}-task.txt").read_text()
    (directory / "000-initial.txt").write_text("Initial build\n" + initial)
    for index, (title, text) in enumerate(tasks, 1):
        (directory / f"{index:03d}-task.txt").write_text(title + "\n" + COMMON + "\n" + text)
print("Prepared 8 bounded tasks per account (16 total).")
