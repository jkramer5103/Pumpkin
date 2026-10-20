# Wither lead attachment

Assignment 53, lane jaron (Christine credentials only). Baseline
`3ea42ff39a626e427378067823c1f72584981bad`, vanilla Java 26.3 / protocol 777.

Right-clicking a Wither with a lead attached it to the player and consumed a lead
in Pumpkin. Vanilla rejects the interaction. The missing eligibility check lives
in the shared mob interaction handler: vanilla `Entity.interact` calls
`Leashable.canHaveALeashAttachedTo`, which dispatches to `Mob.canBeLeashed` and
rejects `Enemy` mobs. Pumpkin already extracts that classification as
`EntityType.is_enemy`. Check it before attaching or consuming the lead.

The change affects callers of `MobEntity::mob_interact` that try to attach a lead
to an enemy mob, including Withers and zombies. Non-enemy attachment and the
earlier existing-leash removal path retain their previous behavior. It does not
change direct leash APIs, leash persistence, distance, movement or drops.

## Focused gameplay regression

`lab/examples/wither-lead-attachment.json` defines a bounded, loaded 32 by 32 arena.
A survival headless client receives two leads in its main hand and right-clicks a
stationary Wither, sheep, then zombie, with each case repeated twice. The target
has NoAI, NoGravity and Silent to isolate attachment without starting a boss fight.
At each `PARITY_LEAD_INTERACT=pp_target` marker, the local interaction driver finds
the target's entity ID from its spawn packet and sends exactly one 26.3
`ServerboundInteractPacket(id, MAIN_HAND, (0,1,0), false)`. A normal command-only
fixture runner cannot supply that packet; its inventory assertions alone are
insufficient evidence without the driver.

The report records the sent interaction, received entity-link packets, initial
and final inventory counts, fixed target position, survival mode and client
liveness. Wither and zombie must produce no attachment packet and retain two
leads; sheep must produce one attachment and retain one. The companion checker
rejects baseline reports unless exactly those eight enemy-attachment/inventory
assertions fail across the two trials:

```
python3 tools/parity-lab/tests/check_wither_lead_attachment.py REPORT.json
python3 tools/parity-lab/tests/check_wither_lead_attachment.py BASELINE.json --baseline
```

Scratch protocol client and driver, source/vanilla hashes, build logs and arena
reports live outside the repository under
`/root/pumpkin-parity-lab/artifacts/jaron-wither53-*`. The first exploratory
vanilla/baseline pair reproduced the difference; final fixture results are
recorded below. No isolated test of the generated classification boolean is
added; the regression exercises the real interaction,
network and inventory paths.

## Upstream and scope

The open PR list and PR3800 leash persistence changes were inspected. PR3800 does
not add attachment eligibility, and PR4092/4107 do not correct this interaction.
Current upstream's handler still lacks this guard. Fork master is already an
ancestor of this campaign branch, so no campaign integration commit was needed.
Source ownership reserves only `entity/mob/mod.rs`, separate from the other
lane's Dragon implementation.

## Validation

All 444 core Rust library tests, workspace formatting, core all-target/all-feature
Clippy and the debug server build passed under the shared Cargo lock with one
build job, disabled debug info/incremental, 5 GiB memory/no swap and 200% CPU
limits. The pre-existing `proc-macro-error2` future-compatibility warning remains.
The copied binary SHA-256 is
`62ae7798626f8f6edea8aa25009fe7afd58fd93dbc420ce543223aef707d424b`.

The identical fixture produced:

| Target | Checks passed | Expected failures | Controlled ticks |
| --- | ---: | ---: | ---: |
| Vanilla 26.3 | 54/54 | 0 | 200 |
| Baseline Pumpkin | 46/54 | 8 | 200 |
| Patched Pumpkin | 54/54 | 0 | 200 |

The eight baseline failures are exactly the Wither/zombie attachment-packet and
inventory checks in both trials. Every sheep control passed. All reports have
matching fixture hashes and gameplay command sequences. Patched source and
copied binary hashes match the successful Rust build. All processes stopped,
cleanup checks passed, and server/client logs contain no error, fatal or panic
entries. Pumpkin save and stop completion markers passed; vanilla final-save
completion was not independently asserted.

The final comparison retains the valid vanilla v3 report and uses v4 Pumpkin
captures, which verify loaded arena corners through block writes before setup.
Initial exploratory captures and earlier Pumpkin captures with failed setup or
position sanity checks are excluded from totals. Cleanup removes death drops
after the tick wait and verifies an empty arena.

Limitations: isolated NoAI mobs, survival main-hand lead attachment, headless
protocol observation. No natural combat, rendered leash visual or full boss-fight
proof. To check visuals with a real client, right-click a Wither with a lead and
expect no rope and no consumption; repeat with a sheep and expect a rope and one
lead consumed. Capture both interactions in a recording before any upstream PR.
