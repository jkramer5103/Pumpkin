use super::{EnderDragonPhase, SitBreathingPhase};
use crate::entity::boss::ender_dragon::{EnderDragonEntity, Vector3Ext};
use pumpkin_util::math::vector3::Vector3;
use pumpkin_world::chunk::ChunkHeightmapType;

pub struct LandingPhase;

impl LandingPhase {
    fn has_arrived(pos: Vector3<f64>, target: Vector3<f64>) -> bool {
        pos.distance_squared(target) < 1.0
    }
}

impl super::Phase for LandingPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::Landing
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    fn get_fly_speed(&self) -> f32 {
        1.5
    }

    fn get_turn_speed(&self, dragon: &EnderDragonEntity) -> f32 {
        let velocity = dragon.mob_entity.living_entity.entity.velocity.load();
        let rot_speed = velocity.x.hypot(velocity.z) as f32 + 1.0;
        rot_speed.min(40.0) / rot_speed
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let entity = &dragon.mob_entity.living_entity.entity;
        let target = {
            let mut target_location = dragon
                .target_location
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            *target_location.get_or_insert_with(|| {
                let origin = *dragon
                    .fight_origin
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                let world = entity.world.load();
                // Pumpkin's heightmap returns the top block, not the space above it.
                let y = world.get_heightmap_height(
                    ChunkHeightmapType::MotionBlockingNoLeaves,
                    origin.0.x,
                    origin.0.z,
                ) + 1;
                Vector3::new(
                    f64::from(origin.0.x) + 0.5,
                    f64::from(y),
                    f64::from(origin.0.z) + 0.5,
                )
            })
        };
        if !Self::has_arrived(entity.pos.load(), target) {
            return;
        }

        SitBreathingPhase::reset_flame_count(dragon);
        dragon.set_phase(EnderDragonPhase::SitScanning);
        *dragon
            .ticks_sitting
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
        *dragon
            .sit_attack_timer
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::LandingPhase;
    use pumpkin_util::math::vector3::Vector3;

    #[test]
    fn landing_requires_strict_three_dimensional_arrival() {
        let target = Vector3::new(0.5, 80.0, 0.5);
        assert!(!LandingPhase::has_arrived(
            Vector3::new(0.5, 100.0, 0.5),
            target
        ));
        assert!(!LandingPhase::has_arrived(
            Vector3::new(0.5, 81.0, 0.5),
            target
        ));
        assert!(!LandingPhase::has_arrived(
            Vector3::new(1.5, 80.0, 0.5),
            target
        ));
        assert!(!LandingPhase::has_arrived(
            Vector3::new(0.5, 80.0, -0.5),
            target
        ));
        assert!(!LandingPhase::has_arrived(
            Vector3::new(1.3, 80.8, 0.5),
            target
        ));
        assert!(LandingPhase::has_arrived(
            Vector3::new(0.5, 80.5, 0.5),
            target
        ));
        assert!(LandingPhase::has_arrived(target, target));
    }
}
