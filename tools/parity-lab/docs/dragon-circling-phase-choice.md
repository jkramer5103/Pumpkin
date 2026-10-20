# Dragon circling phase choices

At a completed circling route, Pumpkin previously chose landing with a fixed
one-in-128 chance. It also chose its possible strafe victim by distance to the
dragon, including creative and spectator players. Vanilla first tries landing
with probability `1 / (aliveCrystals + 3)`, then considers an attackable player
nearest the podium. Its strafe decision uses that player's distance to the
podium and the live crystal count.

The Rust correction makes those decisions before selecting or advancing the
next route. A landing decision enters `LandingApproach` directly. A strafe
decision uses the existing combat target predicate with visibility ignored,
matching `DragonHoldingPatternPhase.findNewTarget` in the official 26.3 server.
The podium uses `MotionBlockingNoLeaves`; Pumpkin's heightmap returns the top
block, so the target height adds one. The existing circling decision boundaries
and route search are unchanged.

The focused regression fixture is
`lab/examples/dragon-circling-phase-choice.json`; its captured-report checker is
`tests/check_dragon_circling_phase_choice.py`. Thirty-two separated dragons start
with initialized nodes, then repeatedly complete routes while held well above
their flight targets. The connected observer is creative. The fixture advances
89 controlled ticks, including loading and initialization, and records twelve
four-tick samples. It checks boss presence, exact tick increments, NoAI and
hovering controls, landing initiation and exclusion of the creative player from
strafing. At least 24 dragons must enter either landing approach or descent by
the final sample. This intentionally measures an aggregate outcome rather than
requiring identical random streams or claiming a measured probability.

Validation passed with the same final fixture and commands on all three servers:

| Target | Checks | Final landing initiations | Final strafing dragons |
| --- | --- | --- | --- |
| Vanilla 26.3 | 44/44 | 32 | 0 |
| Pumpkin before this patch | 42/44 | 6 | 3 |
| Pumpkin with this patch | 44/44 | 32 | 0 |

The baseline failed exactly the landing-initiation and creative-player-exclusion
checks. All presence, tick, NoAI, hovering and cleanup controls passed. Source,
fixture, command-stream and copied-binary hashes were verified. Both Pumpkin
servers completed saves; all scratch processes stopped, with no server or client
errors or panics. Vanilla's final-save completion marker was not observed within
the shutdown grace period. The earlier unbatched fixture exceeded the client's
four-minute lifetime and failed presence controls; that run is retained locally
and excluded from these results.

Under the shared Cargo lock and prescribed resource limits, the following passed:
`cargo fmt --all -- --check`, `cargo test --locked -p pumpkin-core --lib`
(489 tests), `cargo clippy --locked -p pumpkin-core --all-targets --all-features`,
and `cargo build --locked -p pumpkin`. Regression coverage uses the real-world
fixture rather than a new isolated Rust test of the random-choice formulas.

This arena tests phase selection with no End fight manager or crystals. It does
not prove crystal-present probabilities, survival target selection, an entire
landing route, or a whole boss fight. It uses headless protocol clients and
server state; no rendered-client capture is claimed. Landing approach routing
remains a separate candidate: all 32 patched dragons stayed in approach (phase 2),
while all 32 vanilla dragons progressed to descent (phase 3). Pumpkin currently
steers directly to the origin where vanilla follows a path. Multipart collision,
healing/despawn and projectile work remain excluded because of upstream
PR3407, PR3661 and PR3835. Refreshed open-PR searches found no overlapping
circling phase-choice patch.
