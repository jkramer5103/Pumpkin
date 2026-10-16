# Simulation engine integration note

The simulation lane owns infra/, scenarios/, tests/test_scenarios*.py and docs/.
No lab/ files were edited for this campaign.

The current strict scenario schema only accepts `notes` as optional top-level
metadata. It has no prerequisite/capability field. Do not invent one or silently
skip unsupported simulation. `wait_ticks` already verifies freeze and game-time
advancement through `TickController`.

The new opt-in simulation catalog is in `scenarios/simulation/`. It deliberately
stays separate from the immediate-state catalog. `infra/validate_simulation.py`
passes `probe_ticks=True` and explicitly enables `console_arena` for a requested
source console. The normal `lab run --pumpkin-console` CLI currently exposes no
arena switch; changing its CLI belongs to the engine owner. Both paths retain
raw evidence, use the shared engine file lock, and report unsupported timing.
The independent immediate-state validator still rejects wait_ticks rather than
simulating elapsed time.

Potential future prerequisites, for the engine owner to design and validate:
verified deterministic advancement, loaded-and-ticking bounded chunk, supported
state predicate grammar, and observation oracle support. These must be reported
per transport/revision; release RCON and current-source scratch console differ.
A one-tick timing probe alone does not prove longer chunk residency or physics.

Current source rejects terminal `execute if block` and property predicates such
as `minecraft:redstone_lamp[lit=true]`. The water case instead resets a score to
zero, sets it to one through a plain block predicate with `run`, and observes a
terminal score condition supported by both engines. It makes no block-property
claim and does not normalize scoreboard text. Failed conditions stay failures.
