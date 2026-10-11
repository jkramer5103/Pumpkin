# Vanilla 26.3 parity audit and consolidated server

This branch combines fixes from 28 existing Pumpkin pull requests with new fixes found against the official Java Edition 26.3 server. It is a personal combined server branch, not a claim that every vanilla class has been reviewed or every bug is fixed. Existing contributors retain authorship on their cherry-picked commits.

## Reference and coverage

The official Mojang bundler has SHA-1 `33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c`. The inner server contains 7,762 class entries. All were included in batched Vineflower 1.12.0 decompilation, producing 5,037 top-level Java files. CFR 0.152 recovered the two Vineflower fallback classes, `Blocks` and `CopperBulbBlock`; the final source has no remaining decompiler failure placeholders found by the scan.

The semantic review concentrated on flight, fireworks, combat, damage, item consumption and stacking, recipe placement, buckets and dispensers, block growth and survival, sponge traversal, block-state commands, entity persistence, and forced chunk loading. Decompiling the whole JAR does not mean all 5,037 source files were semantically audited. Minecraft source and investigation tools are kept outside the repository.

The branch started at upstream master `3ad20f428`. Duplicate fixes are included intentionally where they were not yet merged: this branch is for one combined server rather than separate upstream submissions.

## New fixes and integration corrections

- Saturation: widen the amplifier before adding one, so amplifier 255 restores food and saturation instead of wrapping to zero. Clamp food after widened addition to prevent high effect levels from wrapping a partially full hunger bar.
- Riptide: reject dry charging and passenger launches; accept flowing water and exposed rain using the entity's water state and feet/head rain checks. Use generated enchantment strength and sound data, add the impulse to existing velocity, and track the 20-tick spin flag, pose and collision attack. Preserve client prediction for the owner, synchronize velocity to observers, and use the active hand for durability and throwing. Normal throws damage the trident before spawning it and use creative-only pickup for creative throws.
- Crops: wheat, carrots, potatoes, beetroot and torchflowers require the vanilla brightness threshold before random growth. Sweet berry growth checks brightness above the bush instead of treating an overhead solid block as the deciding condition.
- Cocoa and nether wart: match vanilla growth/update flags; cocoa uses a uniform one-in-five roll instead of biased modulo arithmetic.
- Bamboo: correct sapling and stalk light checks, the stalk's one-in-three growth chance, total-height counting, and the age test against the stalk two blocks below. Correct the cactus height-loop typo and cap handling.
- Coral: count a coral block's own waterlogged state as water; schedule death after water is removed; use the proper sturdy support face for standing coral and the facing-specific support for wall fans. Dying plants clear waterlogging and send the resulting state to clients.
- Sponges: use connected-water breadth-first traversal with maximum depth six and maximum 64 absorbed positions; drain waterlogged blocks and bubble columns; remove aquatic plants and retain their drops. Preserve the cancellable sponge event and defer neighbour notifications until the sponge is wet to avoid recursive absorption beyond the cap.
- Block bouncing: generate bounce restitution and fall-distance reduction from Extractor data, using the two fields supplied by upstream PR #3741 rather than replacing the rest of the block snapshot. Beds and shelf mushrooms use restitution 0.75. Shelf mushrooms now halve effective fall distance instead of making falls harmless. Elytra collision restitution also uses generated properties.
- `/fill` lighting: update light propagation after batch writes, including strict fills. A live reproduction found a filled stone enclosure still saving skylight 15 and allowing its crop to grow; the fix queues lighting checks for changed light properties.
- `/execute if/unless blocks`: compare complete block states rather than only block types. Masked comparison skips ordinary air as vanilla does. This fixes false matches between blocks with different properties; existing block-entity data comparison limitations remain.
- Native plugins: bump the API version to 4 because the combined changes add fields to public server types. Existing native plugins must be rebuilt against this branch; the public Wasm WIT is unchanged.
- Integration: adapt firework/crossbow item use to the current hand API, remove an overlapping fall-distance helper in favour of the vanilla-shaped flight update, reconcile bucket/dispenser changes, and satisfy the current world-reference and chest control-flow APIs.

## Existing fixes integrated

| Source | Result included |
| --- | --- |
| [#3657](https://github.com/Pumpkin-MC/Pumpkin/pull/3657) | Vanilla-shaped elytra eligibility, flight motion, collision restitution, durability updates, game events and flight-state cleanup, including death/respawn. |
| [#3697](https://github.com/Pumpkin-MC/Pumpkin/pull/3697) | Free and attached firework flight, launch sound, explosions and victim/visibility checks, persistence, crossbow fireworks and multishot handling, dispenser launches, and use-packet rotation. |
| [#3978](https://github.com/Pumpkin-MC/Pumpkin/pull/3978) | Gliding fall-distance cap, reconciled with the elytra flight update rather than retaining two competing helpers. |
| [#4017](https://github.com/Pumpkin-MC/Pumpkin/pull/4017) | Resistance amplifier arithmetic no longer overflows the narrow integer calculation. |
| [#3853](https://github.com/Pumpkin-MC/Pumpkin/pull/3853) | Void damage observes the hurt cooldown. |
| [#3904](https://github.com/Pumpkin-MC/Pumpkin/pull/3904) | Sleeping players wake before accepted damage. |
| [#3666](https://github.com/Pumpkin-MC/Pumpkin/pull/3666) | Damaged items cannot be stacked. |
| [#3976](https://github.com/Pumpkin-MC/Pumpkin/pull/3976) | Placing powder snow returns the empty bucket. |
| [#3975](https://github.com/Pumpkin-MC/Pumpkin/pull/3975) | Jukeboxes consume the correct main-hand/offhand disc outside creative mode. |
| [#3940](https://github.com/Pumpkin-MC/Pumpkin/pull/3940) | Catching bucketable mobs returns the filled mob bucket, including creative filled-result handling. |
| [#3920](https://github.com/Pumpkin-MC/Pumpkin/pull/3920) | Dispensers release the mob stored in a mob bucket. |
| [#3986](https://github.com/Pumpkin-MC/Pumpkin/pull/3986) | Dispensed powder snow sends its block update immediately. |
| [#3990](https://github.com/Pumpkin-MC/Pumpkin/pull/3990) | Dispensed bucket contents replace eligible plants and abort when replacement is cancelled. |
| [#3931](https://github.com/Pumpkin-MC/Pumpkin/pull/3931) | Fence gates can stand above farmland and dirt paths. |
| [#3869](https://github.com/Pumpkin-MC/Pumpkin/pull/3869) | Neighbour updates preserve fire age. |
| [#3868](https://github.com/Pumpkin-MC/Pumpkin/pull/3868) | Unsupported snow is removed by neighbour updates. |
| [#3826](https://github.com/Pumpkin-MC/Pumpkin/pull/3826) | Creative ice breaking does not leave water. |
| [#3865](https://github.com/Pumpkin-MC/Pumpkin/pull/3865) | Withers drop the nether star on death rather than arbitrary removal. |
| [#3977](https://github.com/Pumpkin-MC/Pumpkin/pull/3977) | Finishing consumable use applies `use_remainder`; milk cancellation no longer runs the old unconditional bucket replacement. |
| [#4013](https://github.com/Pumpkin-MC/Pumpkin/pull/4013) | Correct stem brightness checks and farmland updates. |
| [#4015](https://github.com/Pumpkin-MC/Pumpkin/pull/4015) | Double-chest extension works from diagonal placement. |
| [#3922](https://github.com/Pumpkin-MC/Pumpkin/pull/3922) | Recipe-book placement honours item/component stack limits and removes ingredients only from matching stacks. |
| [#3996](https://github.com/Pumpkin-MC/Pumpkin/pull/3996) | Reject non-finite vehicle and Bedrock input positions. |
| [#3706](https://github.com/Pumpkin-MC/Pumpkin/pull/3706) | Reject out-of-range item-stack wire values and correctly replace an enchantments tombstone when enchanting. |
| [#3827](https://github.com/Pumpkin-MC/Pumpkin/pull/3827) | `/setblock` parses and validates block-state properties, including malformed input tests. |
| [#3845](https://github.com/Pumpkin-MC/Pumpkin/pull/3845) | Restore entity motion/UUIDs, load forced chunks through tickets, persist attribute bases/permanent modifiers, apply attack/sweep knockback attributes, and periodically resend status effects. |
| [#3964](https://github.com/Pumpkin-MC/Pumpkin/pull/3964) | `/fill` runs placement callbacks for changed blocks, restoring block entities, flowing water, falling sand and golem-pattern callbacks; strict fills skip these callbacks. |
| [#3741](https://github.com/Pumpkin-MC/Pumpkin/pull/3741) | Extracted block bounce and fall-distance reduction fields, integrated selectively with the current block snapshot. |

PR #3633's VarInt guard was already present on master and was not duplicated. Upstream merge commits were not imported. The imported `/fill` callback patch retains its documented difference from vanilla: callbacks run after the batched region write, which can change results for filtered fills over an existing golem pattern.

## Validation

The Saturation/Riptide follow-up passed 535 selected server, data and plugin tests, including regression coverage for food overflow, Riptide strength/direction and sound-level selection. Saturation was compared with `SaturationMobEffect` and `FoodData`; Riptide was traced through `TridentItem`, enchantment selection, entity rain checks, player spin startup and living-entity spin expiry/collision. An optimized scratch reproduction of the old Saturation handler left food at 19 and saturation at 0 for amplifier 255; the fixed handler produced 20 and 20. On the running server, the user's amplifier-5 command raised saturation from 1.8 to 20. The final core suite was repeated against the committed code: 437 tests passed. Final Clippy covered pumpkin-core, pumpkin-data and pumpkin-codegen with all targets/features; format, dependency and typo checks passed. The installed optimized server loaded the existing three dimensions and answered a protocol-777 status request on localhost:25565. After reconnecting to the updated server, the user confirmed in a real client that Riptide launches with sound and a spin animation in water or exposed rain and refuses charging when dry. Off-hand, collision-attack and creative-pickup checks remain unverified in a real client.

- `cargo fmt --check`, `git diff --check`, `cargo machete`, and `typos` passed.
- `cargo clippy --workspace --all-targets --all-features --locked` passed. Core Clippy was repeated after the final gameplay changes and passed. The only reported warning is the existing dependency future-compatibility notice for `proc-macro-error2`.
- Nextest: 1,018 tests across core, command, protocol, data, NBT, world, inventory and codegen passed; all 10 selected server/Wasm host tests passed. The core suite was repeated after the fill changes: 435 passed. Repeated tests are not counted as additional unique tests.
- Debug server boot, Java status handshake (protocol 777), console commands, world save and clean shutdown passed in an isolated seed-42 world. `/forceload` now loads chunks without a player; the retained baseline could not modify the marked unloaded chunk.
- Live checks and saved chunk NBT confirmed: waterlogged coral survives 140 stepped ticks; coral deprived of water becomes dead coral; drained stairs retain their block but lose waterlogging; unsupported snow disappears; filled water flows; filled sand falls onto its support; filled chests have saved chest block entities.
- Before fluid ticks, console predicates confirmed sponge absorption reaches distance six but leaves distance seven, drains waterlogged stairs, and full-state region comparisons distinguish wet/dry stairs. The capacity fixture leaves exactly 60 water cells from 124 after absorption, proving the 64-cell cap. Water later flowing back into the distance-six cell is expected and is not treated as a depth-test failure.
- Before the fill-lighting fix, the enclosed crop saved skylight 15 and age 7. After it, the same fresh-world fixture saves skylight 0 and age 0, while the exposed control grows to age 7 at random tick speed 4096.

- The optimized release binary passed the same fresh-world runtime and saved-NBT checks, including draining a soul-sand bubble column to air. Both debug and release runs saved and stopped cleanly, with no panics or errors found in their logs.
- The release was built with `CARGO_BUILD_JOBS=1`, `CARGO_INCREMENTAL=0`, and `CARGO_PROFILE_RELEASE_LTO=false`. Disabling LTO limits link memory; this remains an optimized release build. A user systemd scope capped build memory at 5 GiB; observed peak was about 4 GiB.

Earlier intermediate failure logs are retained as investigation evidence and are not final check results. Existing chunks with incorrect saved lighting from older fills are not automatically migrated.

## Server and source

The combined source is on [the fork branch](https://github.com/jkramer5103/Pumpkin/tree/t3code/audit-vanilla-parity-bugs). The local server package is `~/Desktop/Programming_Stuff/Pumpkin-audited-26.3/`; run `start.sh`, then connect using a Java Edition 26.3 client at `localhost:25565`. Console `stop` saves and shuts down. The package uses a separate world and online authentication.

The complete decompiled reference, intermediate evidence and final logs are kept at `~/.local/share/pumpkin-audits/26.3-2026-10-11/`. Investigation tools, vanilla JARs/source and test worlds were not added to the fork.

Reproduce the binary from this branch with:

```bash
CARGO_BUILD_JOBS=1 CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_LTO=false cargo build --locked --release -p pumpkin
```

## Real-client checks still needed

Use a Minecraft Java Edition 26.3 client. The headless client library checked during this audit did not advertise 26.3 support. Console and codec checks do not demonstrate client prediction, sound, animation or GUI correctness.

- In Survival, apply Saturation with amplifier 5 and then 255 while hungry; expect hunger to refill without wrapping or flickering. Saturation itself has no visible HUD bar.
- Charge a Riptide III trident in clear weather outside water; expect use to be rejected. Repeat in exposed rain and flowing water, including with the off hand; expect a launch in the look direction, the Riptide sound and a short spin animation. A dry roofed area must not count as rain. During a spin, hitting a living entity or a wall should end the spin.
- Fly with an elytra, boost with a rocket, collide with a wall and land; verify smooth movement, expected sounds/durability, then die and respawn and start flying again.
- Launch fireworks by hand, crossbow and dispenser; verify trajectory, launch/explosion sounds and nearby damage. Test multishot with limited ammunition and both hands.
- Fall onto a bed, shelf mushroom and slime block; verify bounce and damage, including while sneaking.
- Catch and release a fish in survival and creative, and dispense its bucket. Place powder snow and use a dispenser against a replaceable plant.
- Insert discs with either hand in survival and creative; finish milk/other remainder-producing items and interrupt use before completion.
- Use recipe-book placement with damaged items, different components and altered stack limits; verify inventory contents and ingredient consumption.
- Place a diagonal double chest, remove snow support, break ice in creative, and place a gate over farmland/path.
- Test sleeper damage, high-level Resistance, void damage, Wither death drops, entity reload motion and permanent attribute persistence.

These are outstanding client checks, not tests claimed to have passed. No performance benchmark or optimized release-build comparison has been performed.
