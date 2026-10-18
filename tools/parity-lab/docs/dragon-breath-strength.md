# Uniform Ender Dragon breath damage

Sitting dragon breath should remove three health per contact throughout its cloud. Pumpkin instead applied distance falloff: sheep at the center lost 3 health, halfway sheep lost 1.5, and sheep 4.9 blocks away lost 0.06. Vanilla removes 3 health at all three positions.

`PotionApplicationSource::AreaEffectCloud::instant_scale` now supplies fixed 0.5 potency. Vanilla 26.3's `AreaEffectCloud.serverTick` calls instantaneous effects with 0.5 after checking radius eligibility. `DragonSittingFlamingPhase` adds instant damage at amplifier 0; `HealOrHarmMobEffect.applyInstantaneousEffect` turns that into 3 damage. Pumpkin's generic potion application previously multiplied the distance scale by 0.5. Other clouds, including lingering potions and strafing-created clouds, share this correction. Normal/splash and arrow instant scaling and timed-effect scaling retain their existing behavior.

## Reproduction and validation

`tools/parity-lab/lab/examples/dragon-breath-strength.json` runs two isolated emitted-flame trials with a protocol 777 headless player. After ten emission ticks, it freezes and moves the NoAI dragon away, anchors sheep to the actual cloud center, and checks health after each of two 20-tick contact intervals. Inside positions are 0, 2.5 and 4.9 blocks; an outside control at 5.5 blocks stays healthy. Expected health 8 → 5 → 2 matches vanilla. A Rust regression test checks that different incoming distance scales preserve cloud instant potency while normal application retains its scale.

Clean comparison: vanilla 29/29; baseline 21/29, failing exactly eight middle/edge health checks over two trials. Identical stimulus commands and fixture hashes, exact tick deltas, headless player presence and stopped scratch processes were verified. An initial baseline fixture also counted corpses left until later ticks; that run is retained and excluded. The final fixture counts healthy fresh sheep and was replayed identically on vanilla, baseline and patched Pumpkin.

All 461 pumpkin-core library tests, workspace formatting, core all-targets/all-features Clippy and the debug server build passed under the shared build lock with one Cargo job, disabled debug information/incremental compilation, MemoryMax=5G, MemorySwapMax=0 and CPUQuota=200%. Patched Pumpkin passed all 29 focused checks, matching vanilla. Sheep at every inside position lost exactly 3 health on both contacts, and outside sheep stayed healthy. Identical commands, exact tick deltas, fixture/source/binary hashes and headless player presence were verified. All three scratch processes stopped; Pumpkin save completion markers were verified, while vanilla's final save completion marker was not observed. No error or panic lines appeared in the reviewed server logs. The existing proc-macro-error2 future-compatibility warning remains.

## Scope and remaining work

This is headless server-state evidence, with no rendered-client evidence or complete fight proof. Healing shares the fixed branch but was not live-tested here. Undead effect reversal, integer rounding, timed-effect duration falloff, vertical eligibility, cadence, particles, placement, natural cloud expiration and the sitting attack cycle remain independent.

Open PRs 3407/3661 address hitboxes, 3663 creates creeper clouds, and 3835 handles projectiles; their reviewed patches do not change this scaling path. Fork master 65bca3f is already integrated. Fetched upstream master 998c3f8 retains the defect.
