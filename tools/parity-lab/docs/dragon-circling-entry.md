# Dragon circling phase entry

Pumpkin kept its shared flight target and queued path when entering circling. A dragon returning from another flight phase could keep steering toward that phase's point until it crossed the circling distance threshold. Vanilla Minecraft 26.3 `DragonHoldingPatternPhase.begin` clears both `targetLocation` and `currentPath`; its next server tick chooses a new orbit route. The correction resets those two fields in `CirclingPhase.begin`, preserving orbit direction and the existing path-selection algorithm.

The isolated `dragon-circling-entry.json` regression establishes a hovering target, teleports the dragon to a fixed position with zero velocity, and enters circling. Two trials cover targets forty/eighty blocks above, a lower target, repeated entry, and NoAI. The next vertical position and velocity are compared with vanilla; horizontal coordinates are deliberately unconstrained because route direction and target height are randomized. The original source fails the eight active circling checks. Results and source/binary hashes are retained outside Git.

Fork master was already integrated. Fresh upstream master retains the missing phase-entry override. Open dragon/circling/holding-pattern searches and PR3407/3661/3835 diff review found no duplicate correction. The tracker contact gates are already fixed in earlier campaign commits; multipart/crystal/despawn work remains separate upstream overlap.

Validation:

- All 482 core Rust library tests, workspace formatting, core Clippy with all targets/features, and the debug server build passed under the shared Cargo lock and resource limits.
- The same immutable fixture passes 57/57 primary checks on vanilla and patched Pumpkin; baseline passes 49/57, failing exactly the eight active circling position checks. Both NoAI controls pass. Each target advances 37 controlled ticks across two trials.
- Ten identical pre-tick positions and zero velocities are verified for every target. Patched vertical position and velocity match vanilla in all ten cases, yielding 97/97 checks including those numeric controls. Baseline rises 0.4/0.8 blocks toward higher stale targets or descends 0.4 blocks toward the lower stale target; vanilla and patched Pumpkin descend approximately 0.006 blocks in each active case. Random horizontal trajectories are not compared.
- Fixture/stimulus/source/copied-binary hashes match. Connected headless players, successful final dragon removal and forceload cleanup, stopped scratch processes, and both Pumpkin saves are verified. Logs contain no server errors or panics. Vanilla's final save-completion marker was not observed within the harness shutdown grace period.

Limits: server-state and connected headless-client evidence only; no rendered-client or whole-fight claim. Initial exploratory reports used changing fixture versions and are excluded from the final same-fixture comparison. Existing route selection, lazy node initialization and transition probabilities remain separate unconfirmed leads. The world regression covers target reuse and repeated entry; queued-path clearing follows the vanilla phase-entry lifecycle, without asserting the randomized full orbit. Existing development/debug, offline-mode, Java native-access/deprecation and proc-macro future-compatibility warnings remain.

Manual follow-up: in an isolated arena, let a dragon return from a charge or takeoff into circling and record its new orbit. A human must play-test and attach a real-client recording before opening any upstream PR. Capture: pending real-client recording.
