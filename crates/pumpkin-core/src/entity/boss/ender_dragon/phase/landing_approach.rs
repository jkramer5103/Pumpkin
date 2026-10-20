use super::EnderDragonPhase;
use crate::entity::boss::ender_dragon::{
    DragonNode, EnderDragonEntity, NODE_Y, Vector3Ext, find_path,
};
use pumpkin_util::math::vector3::Vector3;
use pumpkin_world::chunk::ChunkHeightmapType;
use std::collections::VecDeque;
use std::sync::{Mutex, atomic::Ordering};

#[derive(Default)]
pub struct LandingApproachPhase {
    current_path: Mutex<VecDeque<DragonNode>>,
}

impl LandingApproachPhase {
    fn find_new_target(&self, dragon: &EnderDragonEntity) {
        let mut path = self
            .current_path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if path.is_empty() {
            let current_node = dragon.find_closest_node();
            let origin = dragon
                .fight_origin
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .0;
            let world = dragon.mob_entity.living_entity.entity.world.load();
            let egg_y = world.get_heightmap_height(
                ChunkHeightmapType::MotionBlockingNoLeaves,
                origin.x,
                origin.z,
            ) + 1;
            let egg = Vector3::new(f64::from(origin.x), f64::from(egg_y), f64::from(origin.z));
            let target_node = dragon.find_nearest_player(egg).map_or_else(
                || dragon.find_closest_node_to(Vector3::new(40.0, f64::from(egg_y), 0.0)),
                |player| {
                    let pos = player.living_entity.entity.pos.load();
                    let aim = Vector3::new(pos.x, 0.0, pos.z).normalize();
                    dragon.find_closest_node_to(Vector3::new(
                        -aim.x * 40.0,
                        f64::from(NODE_Y),
                        -aim.z * 40.0,
                    ))
                },
            );
            let nodes = dragon
                .nodes
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            // find_path skips the starting node. The podium is a final off-graph node.
            path.extend(
                find_path(
                    &nodes,
                    current_node,
                    target_node,
                    None,
                    dragon.has_alive_crystals(),
                )
                .into_iter()
                .filter_map(|index| nodes[index]),
            );
            path.push_back(DragonNode::new(egg.x, egg.y, egg.z));
        }
        Self::navigate_to_next_path_node(dragon, &mut path);
        let done = path.is_empty();
        drop(path);
        // Vanilla enters descent when the final node is consumed, before flying to it.
        if done {
            dragon.set_phase(EnderDragonPhase::Landing);
        }
    }

    fn navigate_to_next_path_node(dragon: &EnderDragonEntity, path: &mut VecDeque<DragonNode>) {
        if let Some(node) = path.pop_front() {
            let y = f64::from(node.y as f32 + rand::random::<f32>() * 20.0);
            *dragon
                .target_location
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) =
                Some(Vector3::new(node.x, y, node.z));
        }
    }
}

impl super::Phase for LandingApproachPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::LandingApproach
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        self.current_path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clear();
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let entity = &dragon.mob_entity.living_entity.entity;
        let distance = dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .map_or(0.0, |target| entity.pos.load().distance_squared(target));
        if !(100.0..=22500.0).contains(&distance)
            || entity.horizontal_collision.load(Ordering::Relaxed)
        {
            self.find_new_target(dragon);
        }
    }
}
