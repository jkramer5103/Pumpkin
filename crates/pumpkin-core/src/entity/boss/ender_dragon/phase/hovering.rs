use super::EnderDragonPhase;
use crate::entity::boss::ender_dragon::EnderDragonEntity;

pub struct HoveringPhase;

impl super::Phase for HoveringPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::Hovering
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .get_or_insert_with(|| dragon.mob_entity.living_entity.entity.pos.load());
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    fn get_fly_speed(&self) -> f32 {
        1.0
    }
}
