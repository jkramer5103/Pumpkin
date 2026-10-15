# Execute and scoreboard state catalog

The campaign adds 23 distinct scenarios, authored in
`infra/author_execution_scenarios.py`. The original
`python3 infra/author_scenarios.py` entry point reproduces these and the existing
catalog. Pure regeneration was checked against every JSON definition without
writing over unrelated edits.

The experiments cover signed add/remove and multiplication overflow, MIN / -1,
floor division and modulo with a negative divisor, operation-created scores,
objective reset and recreation, strict and inclusive comparisons, cross-objective
equality, range endpoints, missing scores, condition chains, executor self scores,
score-selector ranges/intersections/identity, and stored results/success.
Material substitutions and renamed command sequences do not increase coverage.

Every observation has a nonempty positive expectation. All 23 cases were run
against live vanilla 26.3 twice: **46/46 expectation sets met**, with every raw
setup, step and cleanup response in
`artifacts/jaron-execution-vanilla.json`. Important boundary examples are
2147483647 + 1 = -2147483648, -2147483648 / -1 = -2147483648,
7 / -3 = -3 and 7 % -3 = -2. Missing scores fail zero predicates; explicit
zero scores match; resetting removes them again. These are measured reference
results, not assumptions derived from the Pumpkin implementation.

Run the exact reference suite with:

```sh
python3 - <<'PY'
import subprocess
from infra.author_execution_scenarios import execution_cases
command = ['python3', 'infra/validate_scenarios.py', '--target', 'vanilla',
           '--repeat', '2', '--output', 'artifacts/execution-reference.json']
for scenario in execution_cases():
    command += ['--id', scenario['id']]
raise SystemExit(subprocess.run(command).returncode)
PY
```

The validator acquires the same process file lock as the engine. Catalog
validation happens before connection: duplicate IDs, renamed command sequences,
unknown schema fields and unchecked observations are rejected. Removing
expectations or changing cleanup does not disguise a duplicate experiment.
Focused regressions cover those rejection paths, including verification that an
invalid catalog never opens an RCON connection. The fake disconnect fixture uses
a private test lock while retaining raw interrupted evidence and cleanup checks.

The arena invariant also handles objective names ending in `x`, `y` or `z`;
`pp_aux=2` is a score entry, not an x coordinate. All selectors and marker fixtures
remain bounded. Entity cases observe both included and excluded fixtures where
applicable. Missing command support is retained in raw evidence and is never
converted into a pass. See [integration notes](execute-scoreboard-integration.md)
for current-source limitations and the intentional false store-success condition.
