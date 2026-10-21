# Sitting dragon breath cloud particles

Assignment 67, Christine subscription only. Baseline source:
`545c4347f48410a93eb6548482696f5555a167d9`.

The sitting breath cloud was initialized with colored `ENTITY_EFFECT` particles.
The official 26.3 server initializes this cloud with `DRAGON_BREATH` and power
`1.0`. The different particle type changes how a Java client draws the attack.
This correction adds custom particle selection to the cloud and sets it from
the sitting breath phase before spawning the cloud. Initialization preserves
the selection; ordinary clouds retain their existing potion particle behavior.

The reference is the official 26.3 `DragonSittingFlamingPhase.doServerTick`,
`AreaEffectCloud.setCustomParticle`/`defineSynchedData` and
`PowerParticleOption.streamCodec`. The option payload is a float. Targeted
`javap` output is retained outside the repository in
`artifacts/christine-dragon67-{flaming,cloud,power-particle}.javap`.

The isolated arena uses identical commands on vanilla and campaign baseline:
two trials each of sitting breath, NoAI breath suppression and an ordinary
cloud. It verifies the phase, health, player/dragon positions, cloud presence,
eleven stepped observation ticks, client survival and final cleanup. Cloud
spawn packets identify the breath cloud; decoded metadata must select
`DRAGON_BREATH` with power `1.0`. The ordinary vanilla cloud omits its default
particle metadata; explicit ordinary-cloud particle metadata must remain
`ENTITY_EFFECT`. The fixture and report checker are under
`fixtures/dragon-breath-particle/` and `tests/check_dragon_breath_particle.py`.

Before the fix, vanilla passed 6/6 cases and baseline passed 4/6, failing exactly
the two breath-particle cases. Both emitted clouds at `(16.5, 100, 7.5)`.
Workspace formatting, 492 core Rust library tests, core all-target/all-feature Clippy and the debug server build passed under the shared Cargo lock and resource limits. The patched server passed 6/6 cases, matching vanilla; baseline failed exactly the two breath-particle cases. All command/fixture/source/copied-binary hashes, control checks and six server/client log scans passed. Each target stepped 186 case ticks plus 40 setup and 20 cleanup ticks; scratch processes stopped. See artifacts/christine-dragon67-{rust-validation,live-validation,source-provenance}.json outside the repository.

The initial scratch client lacked loaded/chunk acknowledgments, so its empty
packet captures are excluded. The final probe uses the existing
`WitherBossbarClient`, which supplies those acknowledgments. An initial service
launch also failed before starting a server because it lacked a working
directory. The checker parses numeric coordinates to accept existing SNBT
`100d` versus `100.0d` formatting. None of these exclusions is a source fix. Initial Rust tests and formatting passed; Clippy rejected the separated float suffix. Its spelling was corrected without changing the value or type, then all checks were rerun successfully. The existing proc-macro-error2 future-compatibility notice remains.

Fetched fork master `65bca3f7f36af3b4f5e32ac24ed9abd71c930844` is already an
ancestor of the lane. Fetched upstream master
`44d881c3215692df498182f770ed83fcc426df1f` retains unconditional potion-particle
initialization. Open PRs 3407/3661 cover multipart work, and 4080 exactly covers
the non-player collision lead; those candidates remain deferred. PR 4107's
cloud change only passes effect-source context. Reviewed cloud-related PRs
3663/3816/3835/4105 contain no equivalent cloud/dragon particle correction.

Limits: decoded protocol 777 packets and server state, with no rendered-client,
Bedrock or whole-fight proof. This does not change strafe's direct-cloud attack,
traveling fireballs, cloud persistence, owner attribution, phase metadata,
multipart collisions or healing. The focused world fixture supplies regression
coverage; no mocked Rust getter test was added. For visual checking, observe a
dragon entering sitting flame phase in an isolated arena: its ground cloud
should draw dragon breath particles; a lingering potion should still draw its
normal effect particles.

Durable next lead: natural dragon flight still uses standard-library sin/cos
where official flight steering uses Minecraft lookup-table trigonometry. This
is unconfirmed; reproduce an observable trajectory difference with a controlled
non-cardinal heading before selecting it, and inspect existing math helpers and
upstream overlap. The death-completion game-event omission is source-observed
but currently reaches only plugin hooks in Pumpkin, so it was not selected for
a gameplay reproduction. Never retry the provider-rejected seeded differential
candidate. Read the latest other-lane reservation before touching shared entity/combat files.
