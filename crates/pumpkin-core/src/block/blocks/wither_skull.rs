use pumpkin_data::{
    Block, BlockDirection, BlockId, BlockState, BlockStateId,
    advancement::Advancement,
    entity::EntityType,
    tag::{self, Taggable},
    world::WorldEvent,
};
use pumpkin_macros::pumpkin_block;
use pumpkin_util::{Difficulty, math::position::BlockPos};
use pumpkin_world::world::BlockFlags;
use std::{collections::HashMap, sync::Arc};

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
    blocks: [BlockPos; 9],
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
    find_wither_pattern_in(skull_pos, require_skulls, |pos| {
        world.get_block_state_id(pos)
    })
}

fn find_wither_pattern_in(
    skull_pos: &BlockPos,
    require_skulls: bool,
    mut get_state: impl FnMut(&BlockPos) -> BlockStateId,
) -> Option<WitherPattern> {
    let mut cache = HashMap::new();
    // BlockPattern.find visits positive candidate offsets, X first, then every
    // perpendicular forwards/up pair in Direction declaration order.
    for origin in BlockPos::iterate(*skull_pos, skull_pos.offset((2, 2, 2).into())) {
        for forwards in BlockDirection::all() {
            for up in BlockDirection::all() {
                if up == forwards || up == forwards.opposite() {
                    continue;
                }
                let up_offset = up.to_offset();
                let across = forwards.to_offset().cross(&up_offset);
                let blocks = std::array::from_fn(|index| {
                    origin.offset(across * (index / 3) as i32 - up_offset * (index % 3) as i32)
                });
                if blocks.iter().enumerate().all(|(index, pos)| {
                    let row = index % 3;
                    if row == 0 && !require_skulls {
                        return true;
                    }
                    let (block, state) = *cache
                        .entry(*pos)
                        .or_insert_with(|| BlockState::from_id_with_block(get_state(pos)));
                    match row {
                        0 => matches!(
                            block.id,
                            BlockId::WITHER_SKELETON_SKULL | BlockId::WITHER_SKELETON_WALL_SKULL
                        ),
                        1 => block.has_tag(&tag::Block::MINECRAFT_WITHER_SUMMON_BASE_BLOCKS),
                        _ if index / 3 == 1 => {
                            block.has_tag(&tag::Block::MINECRAFT_WITHER_SUMMON_BASE_BLOCKS)
                        }
                        _ => state.is_air(),
                    }
                }) {
                    return Some(WitherPattern {
                        base: blocks[5],
                        blocks,
                        yaw: if matches!(forwards, BlockDirection::West | BlockDirection::East) {
                            0.0
                        } else {
                            90.0
                        },
                    });
                }
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
        world.set_block_state(
            &pos,
            Block::AIR.default_state.id,
            BlockFlags::NOTIFY_LISTENERS,
        );
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

    // Notify every pattern cell, including air under the arms, after the boss is spawned.
    for pos in &pattern.blocks {
        world.update_neighbors_at(pos, &Block::AIR, None);
    }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matches_rotated_wither_structures_and_rejects_obstructed_arms() {
        // Explicit world coordinates: upright, inverted, flat and sideways T shapes.
        let layouts = [
            (
                [(0, 2, 0), (1, 2, 0), (2, 2, 0)],
                [(0, 1, 0), (1, 1, 0), (2, 1, 0)],
                (1, 0, 0),
                (0, 0, 0),
                90.0,
            ),
            (
                [(0, 0, 0), (1, 0, 0), (2, 0, 0)],
                [(0, 1, 0), (1, 1, 0), (2, 1, 0)],
                (1, 2, 0),
                (0, 2, 0),
                90.0,
            ),
            (
                [(0, 0, 0), (1, 0, 0), (2, 0, 0)],
                [(0, 0, 1), (1, 0, 1), (2, 0, 1)],
                (1, 0, 2),
                (0, 0, 2),
                90.0,
            ),
            (
                [(0, 0, 2), (1, 0, 2), (2, 0, 2)],
                [(0, 0, 1), (1, 0, 1), (2, 0, 1)],
                (1, 0, 0),
                (0, 0, 0),
                90.0,
            ),
            (
                [(0, 0, 0), (0, 1, 0), (0, 2, 0)],
                [(1, 0, 0), (1, 1, 0), (1, 2, 0)],
                (2, 1, 0),
                (2, 0, 0),
                90.0,
            ),
            (
                [(2, 0, 0), (2, 1, 0), (2, 2, 0)],
                [(1, 0, 0), (1, 1, 0), (1, 2, 0)],
                (0, 1, 0),
                (0, 0, 0),
                90.0,
            ),
            (
                [(0, 2, 0), (0, 2, 1), (0, 2, 2)],
                [(0, 1, 0), (0, 1, 1), (0, 1, 2)],
                (0, 0, 1),
                (0, 0, 0),
                0.0,
            ),
        ];
        for (skulls, arms, base, air, yaw) in layouts {
            let pos = |(x, y, z)| BlockPos::new(x, y, z);
            let mut states = HashMap::new();
            for (index, skull) in skulls.into_iter().enumerate() {
                states.insert(
                    pos(skull),
                    if index == 1 {
                        Block::WITHER_SKELETON_WALL_SKULL.default_state.id
                    } else {
                        Block::WITHER_SKELETON_SKULL.default_state.id
                    },
                );
            }
            for arm in arms {
                states.insert(pos(arm), Block::SOUL_SOIL.default_state.id);
            }
            states.insert(pos(base), Block::SOUL_SAND.default_state.id);
            for skull in skulls {
                let find = |states: &HashMap<BlockPos, BlockStateId>, require_skulls| {
                    find_wither_pattern_in(&pos(skull), require_skulls, |p| {
                        states
                            .get(p)
                            .copied()
                            .unwrap_or(Block::AIR.default_state.id)
                    })
                };
                let pattern = find(&states, true).expect("rotated Wither structure");
                assert_eq!(pattern.base, pos(base));
                assert_eq!(pattern.yaw, yaw);
                assert!(states.keys().all(|p| pattern.blocks.contains(p)));
                let mut incomplete = states.clone();
                incomplete.remove(&pos(skull));
                assert!(find(&incomplete, true).is_none());
                assert!(
                    find(&incomplete, false).is_some(),
                    "dispenser base ignores skull row"
                );
                incomplete.remove(&pos(arms[1]));
                assert!(
                    find(&incomplete, false).is_none(),
                    "base still requires every soul block"
                );
                let mut obstructed = states.clone();
                obstructed.insert(pos(air), Block::STONE.default_state.id);
                assert!(find(&obstructed, true).is_none());
                assert!(find(&obstructed, false).is_none());
            }
        }
    }
}
