# Dragon landing arrival

Pumpkin completed the landing phase on its first AI tick, even when the dragon was still above the podium. The correction resolves the target at the bottom center above the fight-origin column's motion-blocking heightmap, excluding leaves. The target is cached until landing starts again. Only a squared distance strictly below one completes landing and resets the perched flame budget. Landing also supplies vanilla's vertical fly speed and velocity-dependent turn speed to the existing dragon steering.

Vanilla reference: Minecraft 26.3 `DragonLandingPhase.doServerTick`, `begin`, `getFlySpeed` and `getTurnSpeed`; `EnderDragonFight.getPodiumLocation` offsets block zero by the fight origin. Pumpkin's heightmap API returns the highest block Y, so landing adds one for the space above it. No changes to the other phases' steering values are included.

The branch includes fork master. Upstream master still completes landing immediately. Open PR3407 implements dragon parts, despawning and crystal work, and changes sitting classification; it does not implement the landing target or arrival gate. PR3661 addresses multipart entity lookup. The tracking issue and parity tracker were used as leads, not as behavior evidence.

## Required heightmap correction

The first patched arena run retained landing correctly but failed arrival because runtime block updates transposed Y and Z when updating heightmaps. Landing depended on an incorrect cached terrain height. This patch integrates only the coordinate-order correction and focused regression from ydw1904's [PR3860](https://github.com/Pumpkin-MC/Pumpkin/pull/3860), head `ba1826fba8fe844c1412521380aee4cec95a161b`, as prerequisite commit `2936d578a28f2a41b7bc540a52fcd8ad752d75f9`. The beacon feature is not included. Open PR3238 also contains a larger heightmap rewrite; this integration keeps the existing implementation and corrects the arguments.

## Validation

Vanilla and patched Pumpkin each passed 28/28 checks; baseline passed 22/28, with six premature-landing failures across two trials. Identical stimuli, fixture hashes, 16 controlled gameplay ticks per target, client presence and stopped scratch processes were verified. The final source hashes match the built and exercised binary. Server and client logs contained no errors or panics; both Pumpkin saves completed. Vanilla's final save-completion marker was not observed within the shutdown grace period.

Under the shared Cargo lock and resource limits, workspace formatting, all 474 core library tests, 35 world chunk tests, core/world all-targets all-features Clippy and the debug server build passed. Each focused regression failed when its old behavior was restored. The initial boss-only build passed Rust checks but failed four live arrival checks, exposing the required heightmap correction; it is not final validation. The exploratory leaf block-state setup was rejected by Pumpkin and is excluded. The final fixture uses plain leaves with random ticks disabled.

Existing development/debug/offline-mode, Java native-access and proc-macro-error2 future-compatibility warnings remain. Validation used a protocol client and server-state commands, without a rendered client.

`dragon-landing-arrival.json` checks two isolated trials of paused landing, an airborne dragon, strict one-block arrival, cached target retention after terrain changes, and re-entry against a higher stone podium below leaves. Teleports isolate arrival from general flight movement. The Rust regression covers the three-dimensional strict arrival boundary.

Limits: headless server-state observations only. No rendered client, particles, complete boss fight, natural landing approach, exact flight trajectory or unloaded target column proof. Existing shared dragon physics and sitting classification are separate from this patch. No upstream PR was opened.
