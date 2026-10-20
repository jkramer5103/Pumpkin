use pumpkin_data::{
    Block, BlockDirection, BlockId, BlockState, BlockStateId, advancement::Advancement,
    entity::EntityType, world::WorldEvent,
};
use pumpkin_macros::pumpkin_block;
use pumpkin_util::{Difficulty, math::position::BlockPos};
use pumpkin_world::world::BlockFlags;
use std::sync::Arc;

use crate::block::entities::skull::SkullBlockEntity;
use crate::{
    block::{
        BlockBehaviour, OnPlaceArgs, PathComputationType, PlacedArgs,
        blocks::skull_block::SkullBlock,
    },
    entity::{Entity, EntityBase, boss::wither::WitherEntity},
    world::World,
};

pub struct WitherPattern {
    blocks: [BlockPos; 7],
    base: BlockPos,
    yaw: f32,
}

#[must_use]
pub fn find_wither_pattern(world: &Arc<World>, skull_pos: &BlockPos) -> Option<WitherPattern> {
    find_wither_pattern_inner(world, skull_pos, true)
}

fn find_wither_pattern_inner(
    world: &Arc<World>,
    skull_pos: &BlockPos,
    require_skulls: bool,
) -> Option<WitherPattern> {
    let is_soul_block = |block: &Block| block == &Block::SOUL_SAND || block == &Block::SOUL_SOIL;
    let is_skull = |pos: &BlockPos| {
        pos == skull_pos
            || matches!(
                world.get_block(pos).id,
                BlockId::WITHER_SKELETON_SKULL | BlockId::WITHER_SKELETON_WALL_SKULL
            )
    };

    for dir in [BlockDirection::North, BlockDirection::West] {
        let opposite = dir.opposite();
        for center in [
            *skull_pos,
            skull_pos.offset(opposite.to_offset()),
            skull_pos.offset(dir.to_offset()),
        ] {
            let top_middle = center.down();
            let base = top_middle.down();
            let arm1 = top_middle.offset(dir.to_offset());
            let arm2 = top_middle.offset(opposite.to_offset());
            let skull1_pos = arm1.up();
            let skull2_pos = arm2.up();

            if is_soul_block(world.get_block(&top_middle))
                && is_soul_block(world.get_block(&base))
                && is_soul_block(world.get_block(&arm1))
                && is_soul_block(world.get_block(&arm2))
                && world.get_block_state(&arm1.down()).is_air()
                && world.get_block_state(&arm2.down()).is_air()
                && (!require_skulls
                    || (is_skull(&center) && is_skull(&skull1_pos) && is_skull(&skull2_pos)))
            {
                return Some(WitherPattern {
                    blocks: [center, skull1_pos, skull2_pos, top_middle, arm1, arm2, base],
                    base,
                    yaw: if dir == BlockDirection::West {
                        90.0
                    } else {
                        0.0
                    },
                });
            }
        }
    }

    None
}

fn spawn_wither(world: &Arc<World>, pattern: &WitherPattern) {
    // Vanilla's pattern caches these states before any construction blocks are cleared.
    let blocks = pattern
        .blocks
        .map(|pos| (pos, world.get_block_state_id(&pos)));
    for (pos, state_id) in blocks {
        world.set_block_state(&pos, Block::AIR.default_state.id, BlockFlags::NOTIFY_ALL);
        world.sync_world_event(
            WorldEvent::ParticlesAndSoundDestroyBlock,
            pos,
            state_id.as_u16().into(),
        );
    }

    let mut spawn_pos = pattern.base.to_f64();
    spawn_pos.y += 0.55;
    let entity = Entity::new(world.clone(), spawn_pos, &EntityType::WITHER);
    entity.yaw.store(pattern.yaw);
    entity.body_yaw.store(pattern.yaw);
    let wither = WitherEntity::new(entity);
    wither.make_invulnerable();
    let advancement_box = wither.get_entity().bounding_box.load().expand_all(50.0);
    for player in world.get_players_at_box(&advancement_box) {
        if !player.is_spectator() {
            player.trigger_advancement_criterion(Advancement::NETHER_SUMMON_WITHER, "summoned");
        }
    }
    world.spawn_entity(wither);
}

#[pumpkin_block("wither_skeleton_skull")]
pub struct WitherSkeletonSkullBlock;

impl WitherSkeletonSkullBlock {
    /// Checks whether a dispenser can place a skull on a Wither summon base.
    pub fn can_spawn_mob(world: &Arc<World>, skull_pos: &BlockPos) -> bool {
        skull_pos.0.y >= world.get_bottom_y() + 2
            && world.level_info.load().difficulty != Difficulty::Peaceful
            && find_wither_pattern_inner(world, skull_pos, false).is_some()
    }
}

impl BlockBehaviour for WitherSkeletonSkullBlock {
    fn on_place(&self, args: OnPlaceArgs<'_>) -> BlockStateId {
        SkullBlock::on_place(&SkullBlock, args)
    }

    fn placed(&self, args: PlacedArgs<'_>) {
        args.world
            .add_block_entity(Arc::new(SkullBlockEntity::new(*args.position)));

        if args.world.level_info.load().difficulty == Difficulty::Peaceful {
            return;
        }

        if let Some(pattern) = find_wither_pattern(args.world, args.position) {
            spawn_wither(args.world, &pattern);
        }
    }

    fn is_pathfindable(&self, _state: &BlockState, _computation_type: PathComputationType) -> bool {
        false
    }
}
