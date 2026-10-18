# Wither side-head firing slots

Source commit: `b667aeaf8bbca1e98fff00c8155c01ca0e4be170`.

With distinct targets in its two side-head slots, Pumpkin fired each skull from the opposite physical side compared with vanilla 26.3. Both side-head calls now pass `i + 1` as the firing-head index, matching vanilla for targeted and idle attacks. Slot storage, cooldowns, target selection, head geometry, scale and projectile flight retain their existing code.

Vanilla review followed `WitherBoss.customServerAiStep`, both `performRangedAttack` overloads and `getHeadX/Y/Z`. Alternative target slots 1 and 2 select firing-head indices 2 and 3. In the bounded forward-facing arena these fire from negative and positive X respectively. This offset is separate from the earlier launch-height/radius/scale fixes. No vanilla source is published here.

The opt-in fixture `lab/examples/wither-side-head-firing-slots.json` places a Wither at (8,80,3) and two stationary sheep at (4,80,13), (12,80,13), inside one chunk. A creative protocol777 headless client records spawn and entity-metadata packets. Each trial resets boss position, yaw and velocity before each of 25 individual ticks. Skulls are removed after capture, before their next tick. The boss and both sheep must retain full health.

The focused regression checker `tests/check_wither_side_head_packets.py REPORT.json` independently reads raw tick packets. It resolves sheep entity IDs, reads the preceding Wither target slots (metadata 17/18), and associates each skull's initial horizontal direction with a victim. Direction cosines must identify one victim clearly, and origin projections must remain unambiguous. Equal-target trials cannot distinguish the slots; at least two distinct-target trials must cover both sides. The fixture's command-only health controls do not detect this bug.

All 443 core Rust library tests, workspace formatting, core Clippy with all targets/features, and the debug server build passed under the shared Cargo lock with one job, disabled debug info/incremental compilation and the required resource caps. The existing `proc-macro-error2` future-compatibility warning remains.

Final fresh-world capture results: vanilla 4/4 matching skulls in two distinct-target trials; patched Pumpkin 4/4 in two trials; baseline 0/10 in five trials, failing specifically `Wrong side-head firing slot`. The six initial final vanilla trials contained only one distinct-target pair, so one additional fresh vanilla trial supplied the second; all seven trials are retained. Row-level controls passed 70/70 for vanilla and 60/60 for patched Pumpkin. Baseline passed 55/60, failing only its five correspondence controls. Equal-target rows still exercise health/client/environment controls, but contribute no correspondence evidence.

The identical fixture stimulus, 25-tick windows, source hash and baseline/patched binary hashes were verified. All 19 scratch processes stopped; all 12 Pumpkin shutdown completion markers were present. Seven vanilla logs contain stopping/saving messages without a complete shutdown marker within harness grace. Server/client logs contain no errors, exceptions or panics; existing Java native/Unsafe and debug-server warnings remain. Patched binary SHA-256: `8fef8d610f5f6f1b623d6c60455bb8eff6a662712015296ab089ee88538b6e4d`. Local evidence: `artifacts/jaron-wither28-validation.json`, `artifacts/jaron-wither28-verify.json` and `artifacts/jaron-wither28-source-provenance.json`.

To recapture: freeze an isolated flat server with a connected creative client; run the fixture setup and record raw packets in one-tick windows while executing its steps. Wait for entity work after each verified tick barrier and use a fresh scratch server for every trial. Store each trial's raw packets as `rows[].ticks[].packets`, the tick as `tick`, and actual health/client/environment checks as `rows[].checks`. Mark `complete` and `stopped` only after capture and cleanup. Run the checker on vanilla, baseline and patched reports. The local capture driver is `artifacts/jaron-wither28-probe.py`; downloaded/decompiled vanilla and raw artifacts are excluded from publication.

Fork master `65bca3f` is already an ancestor. Fetched upstream `998c3f8` retains the two incorrect call sites. Open Wither PRs were rechecked before push, including [3835](https://github.com/Pumpkin-MC/Pumpkin/pull/3835) for projectile impacts and [4092](https://github.com/Pumpkin-MC/Pumpkin/pull/4092) for AI foundations; neither changes this offset. No upstream implementation was copied.

Initial captures are preserved and excluded: a cross-chunk arena lacked complete entity tracking; a reused-world baseline had an unsupported mob-effect command and first-tick sheep-health failures; a subsequent baseline had three unloaded far-corner floor setup failures. Final captures omit the effect command, restrict floor/forceload setup to the occupied chunk and use fresh worlds/processes. Four own historical binaries were losslessly archived with verified decompressed hashes to preserve build headroom.

Limitations: headless packets/server state only, with no rendered-client capture or whole-fight proof. Random idle shots were source-reviewed but not exercised by this easy-difficulty targeted-shot fixture. Body yaw versus entity yaw remains an independent unconfirmed lead that intersects the AI-foundation PR. Generic flight, impact, damage effects and kill credit are outside this correction.

Manual play test: summon a Wither with two separated targets in a private arena; expect vanilla's target-to-shot correspondence. Record the boss and both targets through several side-head shots.

Capture: <attach screenshot or recording here>
