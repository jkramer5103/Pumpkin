use super::{EnderDragonPhase, SitBreathingPhase};
use crate::entity::boss::ender_dragon::EnderDragonEntity;

pub struct LandingPhase;

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

    fn tick(&self, dragon: &EnderDragonEntity) {
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
