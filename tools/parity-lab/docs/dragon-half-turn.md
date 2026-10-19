# Dragon flight reversal direction

A hovering dragon establishes a target, then is placed 30 blocks along negative Z from it with yaw zero and zero velocity. On its next AI tick vanilla turns to -3.5 degrees; the old Pumpkin calculation chooses +3.5 degrees. Its lateral movement also goes in the opposite direction. Reversing the starting orientation exposes the same error.

Vanilla wraps the requested turn into [-180,180), while Pumpkin retained +180 before clamping to the steering limit. The correction uses the existing degree-wrap helper. The turn-speed calculation and other angles retain their behavior.

Reference: official 26.3 EnderDragon.aiStep steering and DragonHoverPhase target initialization. Upstream master c7a234ab8 still contains the old calculation. Reviewed open PRs [3407](https://github.com/Pumpkin-MC/Pumpkin/pull/3407), [3661](https://github.com/Pumpkin-MC/Pumpkin/pull/3661), [3835](https://github.com/Pumpkin-MC/Pumpkin/pull/3835) and [4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092) do not change this calculation. Fork master was already an ancestor of the campaign branch. Source hashes and review evidence are retained in the private lab artifacts.

Validation:

- Workspace formatting, all 481 pumpkin-core library tests, core all-targets/all-features Clippy and the debug server build passed under the shared Cargo lock and resource limits. Restoring the old calculation made the focused reversal regression fail with +50 instead of -50.
- Two isolated arena trials used identical stimuli and 24 controlled ticks per target. Vanilla and the patched binary passed 62/62 checks; baseline Pumpkin passed 50/62, failing exactly the yaw, lateral position and lateral velocity checks for both reversal orientations in both trials. Adjacent headings, straight flight and NoAI controls passed on all three targets.
- The committed dragon-half-turn.json fixture retains the yaw assertions and position/motion observations; the private arena runner additionally checks lateral signs from those observations. Fixture, stimulus, source and copied binary hashes match. The connected headless client and stopped scratch servers were verified. No ERROR/panic lines were observed; both Pumpkin servers completed saves.

Limits: controlled steering with a headless protocol client and server-state observations only; no rendered-client capture, complete fight or natural-trajectory proof. General travel ordering, yaw accumulation, collision termination, multipart registration and crystal behavior remain separate work. Vanilla final-save completion was not observed within the shutdown grace period, though process stop was verified. An initial exploratory fixture used unsupported scaled data queries and centered coordinates; it is excluded from the final comparison. Existing development/debug/offline-mode/Java native-access and proc-macro-error2 future-compatibility warnings remain.
