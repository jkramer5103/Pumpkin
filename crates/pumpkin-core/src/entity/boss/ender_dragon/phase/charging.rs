use super::EnderDragonPhase;
use crate::entity::boss::ender_dragon::{EnderDragonEntity, Vector3Ext};
use std::sync::atomic::Ordering;

const CHARGE_RECOVERY_TIME: i32 = 10;

pub struct ChargingPhase;

impl ChargingPhase {
    fn should_end_charge(
        time_since_charge: &mut i32,
        distance_squared: Option<f64>,
        collided: bool,
    ) -> bool {
        let Some(distance_squared) = distance_squared else {
            return true;
        };
        if *time_since_charge > 0 {
            let elapsed = *time_since_charge;
            *time_since_charge += 1;
            if elapsed >= CHARGE_RECOVERY_TIME {
                return true;
            }
        }
        // Vanilla increments again while the dragon remains near/far or colliding.
        if !(100.0..=22500.0).contains(&distance_squared) || collided {
            *time_since_charge += 1;
        }
        false
    }
}

impl super::Phase for ChargingPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::Charging
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
        *dragon
            .time_since_charge
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
    }

    fn end(&self, dragon: &EnderDragonEntity) {
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let entity = &dragon.mob_entity.living_entity.entity;
        let target = *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if target.is_none() {
            tracing::warn!("Aborting charge player as no target was set.");
        }
        let should_end = Self::should_end_charge(
            &mut dragon
                .time_since_charge
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
            target.map(|target| entity.pos.load().distance_squared(target)),
            entity.horizontal_collision.load(Ordering::Relaxed),
        );
        if should_end {
            dragon.set_phase(EnderDragonPhase::Circling);
        }
    }

    fn get_fly_speed(&self) -> f32 {
        3.0
    }
}

#[cfg(test)]
mod tests {
    use super::ChargingPhase;

    #[test]
    fn charge_recovery_keeps_running_after_leaving_the_target() {
        let mut time = 0;
        assert!(!ChargingPhase::should_end_charge(
            &mut time,
            Some(99.0),
            false
        ));
        for _ in 0..9 {
            assert!(!ChargingPhase::should_end_charge(
                &mut time,
                Some(400.0),
                false
            ));
        }
        assert!(ChargingPhase::should_end_charge(
            &mut time,
            Some(400.0),
            false
        ));
    }

    #[test]
    fn charge_recovery_uses_strict_distance_bounds_and_collision() {
        for distance in [100.0, 22500.0] {
            let mut time = 0;
            for _ in 0..20 {
                assert!(!ChargingPhase::should_end_charge(
                    &mut time,
                    Some(distance),
                    false
                ));
            }
            assert_eq!(time, 0);
        }
        for (distance, collided) in [(99.0, false), (22501.0, false), (400.0, true)] {
            let mut time = 0;
            for _ in 0..6 {
                assert!(!ChargingPhase::should_end_charge(
                    &mut time,
                    Some(distance),
                    collided
                ));
            }
            assert!(ChargingPhase::should_end_charge(
                &mut time,
                Some(distance),
                collided
            ));
        }
    }

    #[test]
    fn charge_without_a_target_ends_immediately() {
        assert!(ChargingPhase::should_end_charge(&mut 0, None, false));
    }
}
