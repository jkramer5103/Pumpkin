use super::EnderDragonPhase;
use crate::entity::boss::ender_dragon::{EnderDragonEntity, NODE_Y};
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
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let origin = {
            let guard = dragon
                .fight_origin
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            guard.0
        };
        // Vanilla initializes its flight target before checking podium departure.
        if self.first_tick.swap(false, Ordering::Relaxed) {
            *dragon
                .target_location
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) = Some(Vector3::new(
                f64::from(origin.x),
                f64::from(NODE_Y),
                f64::from(origin.z),
            ));
            return;
        }

        let entity = &dragon.mob_entity.living_entity.entity;
        let world = entity.world.load();
        // Pumpkin's heightmap returns the top block, not the space above it.
        let y = world.get_heightmap_height(
            ChunkHeightmapType::MotionBlockingNoLeaves,
            origin.x,
            origin.z,
        ) + 1;
        if Self::has_left_podium(entity.pos.load(), BlockPos::new(origin.x, y, origin.z)) {
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
