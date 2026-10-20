use super::EnderDragonPhase;
use crate::entity::boss::ender_dragon::{EnderDragonEntity, NODE_Y, find_path};
use pumpkin_util::math::position::BlockPos;
use pumpkin_util::math::vector3::Vector3;
use pumpkin_world::chunk::ChunkHeightmapType;
use std::sync::atomic::{AtomicBool, Ordering};

pub struct TakingOffPhase {
    first_tick: AtomicBool,
}

impl Default for TakingOffPhase {
    fn default() -> Self {
        Self {
            first_tick: AtomicBool::new(true),
        }
    }
}

impl TakingOffPhase {
    fn has_left_podium(pos: Vector3<f64>, podium: BlockPos) -> bool {
        podium.dist_to_center_sqr(pos.x, pos.y, pos.z) >= 100.0
    }

    fn find_new_target(dragon: &EnderDragonEntity, podium: BlockPos) {
        let entity = &dragon.mob_entity.living_entity.entity;
        let pos = entity.pos.load();
        let current_node = dragon.find_closest_node();
        // EnderDragon.getHeadLookVector tilts the head by its distance from the podium.
        let dist = ((podium.dist_to_center_sqr(pos.x, pos.y, pos.z).sqrt() as f32) / 4.0).max(1.0);
        let look = Vector3::from_yaw_pitch(entity.yaw.load(), -6.0 / dist * 1.5 * 5.0);
        let target_node = dragon.find_closest_node_to(Vector3::new(
            -look.x * 40.0,
            f64::from(NODE_Y),
            -look.z * 40.0,
        ));
        let world = entity.world.load();
        let crystals_alive = world.dragon_fight.as_ref().is_some_and(|fight| {
            fight
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .alive_crystals()
                > 0
        });
        let target_node = if crystals_alive {
            target_node % 12
        } else {
            ((target_node as i32 - 12) & 7) as usize + 12
        };
        let nodes = dragon
            .nodes
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        // find_path already skips the starting node, unlike vanilla's Path.
        let mut path = find_path(&nodes, current_node, target_node, None, crystals_alive);
        let target = path.first().and_then(|&index| nodes[index]).map(|node| {
            Vector3::new(
                node.x,
                f64::from(node.y as f32 + rand::random::<f32>() * 20.0),
                node.z,
            )
        });
        if target.is_some() {
            path.remove(0);
        }
        drop(nodes);
        *dragon
            .path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = path;
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = target;
    }
}

impl super::Phase for TakingOffPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::TakingOff
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        self.first_tick.store(true, Ordering::Relaxed);
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
        dragon
            .path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clear();
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let origin = {
            let guard = dragon
                .fight_origin
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            guard.0
        };
        let entity = &dragon.mob_entity.living_entity.entity;
        let world = entity.world.load();
        // Pumpkin's heightmap returns the top block, not the space above it.
        let y = world.get_heightmap_height(
            ChunkHeightmapType::MotionBlockingNoLeaves,
            origin.x,
            origin.z,
        ) + 1;
        let podium = BlockPos::new(origin.x, y, origin.z);
        // Vanilla initializes its flight target before checking podium departure.
        if self.first_tick.swap(false, Ordering::Relaxed) {
            Self::find_new_target(dragon, podium);
            return;
        }
        if Self::has_left_podium(entity.pos.load(), podium) {
            dragon.set_phase(EnderDragonPhase::Circling);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::TakingOffPhase;
    use pumpkin_util::math::position::BlockPos;
    use pumpkin_util::math::vector3::Vector3;

    #[test]
    fn takeoff_ends_at_the_observed_three_dimensional_podium_boundary() {
        let podium = BlockPos::new(0, 80, 0);
        for (pos, departed) in [
            (Vector3::new(10.499, 80.5, 0.5), false),
            (Vector3::new(10.5, 80.5, 0.5), true),
            (Vector3::new(-9.501, 80.5, 0.5), true),
            (Vector3::new(0.5, 90.499, 0.5), false),
            (Vector3::new(0.5, 90.5, 0.5), true),
            (Vector3::new(8.5, 80.5, 6.499), false),
            (Vector3::new(8.5, 80.5, 6.501), true),
        ] {
            assert_eq!(TakingOffPhase::has_left_podium(pos, podium), departed);
        }
        assert!(TakingOffPhase::has_left_podium(
            Vector3::new(0.5, 120.5, 0.5),
            BlockPos::new(0, 110, 0),
        ));
    }
}
