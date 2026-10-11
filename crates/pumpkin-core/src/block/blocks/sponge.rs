use pumpkin_macros::pumpkin_block;
use pumpkin_util::math::vector3::Vector3;
use std::collections::{HashSet, VecDeque};
use std::sync::Arc;

use crate::block::{BlockBehaviour, OnNeighborUpdateArgs, PlacedArgs};
use pumpkin_data::particle::Particle;
use pumpkin_data::sound::{Sound, SoundCategory};
use pumpkin_data::{Block, BlockDirection, BlockStateId};
use pumpkin_util::math::position::BlockPos;
use pumpkin_world::world::BlockFlags;

#[pumpkin_block("minecraft:sponge")]
pub struct SpongeBlock;

impl SpongeBlock {
    const MAX_DEPTH: u8 = 6;
    const MAX_COUNT: usize = 64;

    pub fn absorb_water(world: &Arc<crate::world::World>, position: &BlockPos) -> bool {
        let mut water_blocks = Vec::new();
        let mut visited = HashSet::from([*position]);
        let mut queue = VecDeque::from([(*position, 0)]);

        while let Some((current_pos, depth)) = queue.pop_front() {
            if depth == Self::MAX_DEPTH {
                continue;
            }
            for direction in BlockDirection::all() {
                let next_pos = current_pos.offset(direction.to_offset());
                if water_blocks.len() == Self::MAX_COUNT || !visited.insert(next_pos) {
                    continue;
                }
                let (block, state) = world.get_block_and_state_id(&next_pos);
                let aquatic_plant = matches!(
                    block.id,
                    pumpkin_data::BlockId::KELP
                        | pumpkin_data::BlockId::KELP_PLANT
                        | pumpkin_data::BlockId::SEAGRASS
                        | pumpkin_data::BlockId::TALL_SEAGRASS
                );
                let replacement =
                    if block == &Block::WATER || block == &Block::BUBBLE_COLUMN || aquatic_plant {
                        BlockStateId::AIR
                    } else if let Some(dry_state) = block.set_waterlogged(state, false)
                        && state.is_waterlogged()
                    {
                        dry_state
                    } else {
                        continue;
                    };
                water_blocks.push((next_pos, block, state, replacement, aquatic_plant));
                queue.push_back((next_pos, depth + 1));
            }
        }

        if water_blocks.is_empty() {
            return false;
        }
        let mut event =
            crate::plugin::api::events::block::sponge_absorb::SpongeAbsorbEvent::new(*position);
        if let Some(server) = world.server.upgrade() {
            server.plugin_manager.fire_blocking(&server, &mut event);
        }
        if event.cancelled {
            return false;
        }

        for (water_pos, block, state, replacement, aquatic_plant) in &water_blocks {
            if *aquatic_plant {
                crate::block::drop_loot(
                    world,
                    block,
                    water_pos,
                    true,
                    &crate::world::loot::LootContextParameters {
                        block_state: Some(pumpkin_data::BlockState::from_id(*state)),
                        position: Some(water_pos.to_f64()),
                        ..Default::default()
                    },
                );
            }
            // Defer neighbour notifications until the sponge is wet, preventing recursive absorption.
            world.set_block_state(water_pos, *replacement, BlockFlags::NOTIFY_LISTENERS);
        }
        world.set_block_state(
            position,
            Block::WET_SPONGE.default_state.id,
            BlockFlags::NOTIFY_ALL,
        );
        for (water_pos, block, _, _, _) in water_blocks {
            world.update_neighbors_at(&water_pos, block, None);
        }
        world.play_block_sound(Sound::BlockSpongeAbsorb, SoundCategory::Blocks, *position);
        true
    }
}

impl BlockBehaviour for SpongeBlock {
    fn placed(&self, args: PlacedArgs<'_>) {
        Self::absorb_water(args.world, args.position);
    }

    fn on_neighbor_update(&self, args: OnNeighborUpdateArgs<'_>) {
        Self::absorb_water(args.world, args.position);
    }
}

#[pumpkin_block("minecraft:wet_sponge")]
pub struct WetSpongeBlock;

impl BlockBehaviour for WetSpongeBlock {
    fn placed(&self, args: PlacedArgs<'_>) {
        {
            // Check if placed where water evaporates (EnvironmentAttributes.WATER_EVAPORATES), if so, dry out
            if args.world.dimension.water_evaporates {
                args.world.set_block_state(
                    args.position,
                    Block::SPONGE.default_state.id,
                    BlockFlags::NOTIFY_ALL,
                );

                // Play dry sound and spawn smoke particles
                args.world.play_block_sound(
                    Sound::BlockWetSpongeDries,
                    SoundCategory::Blocks,
                    *args.position,
                );

                args.world.spawn_particle(
                    Vector3::new(
                        args.position.0.x as f64 + 0.5,
                        args.position.0.y as f64 + 1.0,
                        args.position.0.z as f64 + 0.5,
                    ),
                    Vector3::new(0.25, 0.0, 0.25),
                    0.01,
                    16,
                    Particle::Cloud,
                );
            }
        }
    }
}
