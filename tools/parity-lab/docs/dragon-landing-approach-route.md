# Dragon landing approach route

Pumpkin's landing approach previously targeted the fight origin directly and
waited until the dragon was within one block before entering descent. Vanilla
26.3 `DragonLandingApproachPhase` instead follows a flight-node path ending at
the non-leaf podium height. It enters descent when it consumes the final node,
before the dragon reaches that node. The descent phase then steers to the
centered podium target.

The Rust correction gives the approach phase its own route. It selects the
approach node opposite the attackable player nearest the podium, or the eastern
node when there is no eligible player. It uses the existing dragon graph search
and adds the podium as an off-graph final waypoint. The graph search receives
no final node because its return type contains graph indices; this also keeps
the heuristic aimed at the graph destination. Existing callers are unchanged.
Entering the phase clears its route and shared steering target. Target proximity,
a target more than 150 blocks away, or horizontal collision advances the route.
Waypoint heights use vanilla's float jitter.

The focused regression is `lab/examples/dragon-landing-approach-route.json`, with
captured-report checker `tests/check_dragon_landing_approach_route.py`. It uses a
stone podium at y79 in a scratch overworld, a creative headless observer, and
four dragons. A short route must start descent after one tick while still far
from the podium. A longer route must remain in approach initially and reach
descent after distant-target teleports consume its waypoints. Re-entry must
rebuild the longer route. NoAI and hovering controls, exact tick increments,
four-boss presence and cleanup are checked. Teleports isolate route progression
from independent flight-physics differences.

The identical final fixture advanced 59 controlled ticks on each target:

| Target | Checks | Result |
| --- | --- | --- |
| Vanilla 26.3 | 31/31 | All descent and route controls passed |
| Pumpkin before this patch | 28/31 | Failed exactly the three descent transitions |
| Pumpkin with this patch | 31/31 | All descent and route controls passed |

The initial phase, re-entry, NoAI, hovering, four-boss presence, tick increments
and cleanup controls passed on all three targets. Source, fixture, command-stream
and copied-binary hashes were verified. Both Pumpkin servers completed saves;
all scratch servers stopped, with no server or client errors or panics. Vanilla's
final-save completion marker was not observed within the shutdown grace period.

Under the shared Cargo lock with the prescribed resource limits, these passed:
`cargo fmt --all -- --check`, `cargo test --locked -p pumpkin-core --lib`
(489 tests), `cargo clippy --locked -p pumpkin-core --all-targets --all-features`,
and `cargo build --locked -p pumpkin`. Regression coverage exercises the real
server fixture; there is no new isolated Rust unit test. The first Rust attempt
passed formatting and tests but stopped on the repository's required
`Option::map_or_else` style. That was corrected before the final passing run.
The existing `proc-macro-error2` future-compatibility notice remains.

The first discovery run lacked a raised podium;
its low void-world height made vanilla's target-node lookup fall back to node 0.
That invalidated the short/long-route setup expectations. Its evidence is
retained locally and excluded; the corrected fixture explicitly creates the
podium and initializes the longer route near the flight ring.

This is headless server-state evidence, without a rendered-client capture or
whole-fight proof. The isolated arena has no End fight manager or crystals and
does not test survival-player approach selection, natural landing flight, or
unreachable graph routes. Pumpkin lacks vanilla's separate vertical-collision
state, so that route-advance trigger remains deferred. Multipart, healing and
projectile work remain excluded for open upstream PR3407, PR3661 and PR3835.
Refreshed open-PR searches found no landing-approach route implementation overlap;
PR3407 touches a different phase-manager classification, outside this change.
