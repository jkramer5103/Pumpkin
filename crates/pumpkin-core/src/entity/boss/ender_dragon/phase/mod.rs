use crate::entity::boss::ender_dragon::EnderDragonEntity;
use pumpkin_util::math::vector3::Vector3;
use std::sync::Arc;

mod charging;
mod circling;
mod dying;
mod fly_to_portal;
mod hovering;
mod landing;
mod landing_approach;
mod sit_attacking;
mod sit_breathing;
mod sit_scanning;
mod strafing;
mod taking_off;

pub use charging::ChargingPhase;
pub use circling::CirclingPhase;
pub use dying::DyingPhase;
pub use fly_to_portal::FlyToPortalPhase;
pub use hovering::HoveringPhase;
pub use landing::LandingPhase;
pub use landing_approach::LandingApproachPhase;
pub use sit_attacking::SitAttackingPhase;
pub use sit_breathing::SitBreathingPhase;
pub use sit_scanning::SitScanningPhase;
pub use strafing::StrafingPhase;
pub use taking_off::TakingOffPhase;

fn default_turn_speed(velocity: Vector3<f64>) -> f32 {
    let rot_speed = velocity.x.hypot(velocity.z) as f32 + 1.0;
    0.7 / rot_speed.min(40.0) / rot_speed
}

pub trait Phase: Send + Sync {
    fn get_type(&self) -> EnderDragonPhase;
    fn tick(&self, dragon: &EnderDragonEntity);
    fn begin(&self, _dragon: &EnderDragonEntity) {}
    fn end(&self, _dragon: &EnderDragonEntity) {}
    fn is_sitting(&self) -> bool {
        false
    }
    fn get_fly_speed(&self) -> f32 {
        0.6
    }
    fn get_turn_speed(&self, dragon: &EnderDragonEntity) -> f32 {
        default_turn_speed(dragon.mob_entity.living_entity.entity.velocity.load())
    }
    fn get_fly_target_location(&self) -> Option<Vector3<f64>> {
        None
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum EnderDragonPhase {
    #[default]
    Circling = 0,
    Strafing = 1,
    Charging = 2,
    FlyToPortal = 3,
    LandingApproach = 4,
    Landing = 5,
    SitAttacking = 6,
    SitBreathing = 7,
    TakingOff = 8,
    Hovering = 9,
    Dying = 10,
    SitScanning = 11,
}

impl EnderDragonPhase {
    #[must_use]
    pub const fn is_sitting(self) -> bool {
        matches!(
            self,
            Self::LandingApproach
                | Self::Landing
                | Self::SitScanning
                | Self::SitAttacking
                | Self::SitBreathing
                | Self::TakingOff
        )
    }

    #[must_use]
    pub const fn network_id(self) -> i32 {
        match self {
            Self::Circling => 0,
            Self::Strafing => 1,
            Self::FlyToPortal | Self::LandingApproach => 2,
            Self::Landing => 3,
            Self::TakingOff => 4,
            Self::SitBreathing => 5,
            Self::SitScanning => 6,
            Self::SitAttacking => 7,
            Self::Charging => 8,
            Self::Dying => 9,
            Self::Hovering => 10,
        }
    }

    #[must_use]
    pub const fn from_network_id(id: i32) -> Option<Self> {
        Some(match id {
            1 => Self::Strafing,
            2 => Self::LandingApproach,
            3 => Self::Landing,
            4 => Self::TakingOff,
            5 => Self::SitBreathing,
            6 => Self::SitScanning,
            7 => Self::SitAttacking,
            8 => Self::Charging,
            9 => Self::Dying,
            10 => Self::Hovering,
            // Holding pattern (0) is also vanilla's fallback for invalid IDs.
            _ => Self::Circling,
        })
    }
}

pub struct PhaseManager {
    phases: [Arc<dyn Phase>; 12],
}

impl Default for PhaseManager {
    fn default() -> Self {
        Self::new()
    }
}

impl PhaseManager {
    #[must_use]
    pub fn new() -> Self {
        Self {
            phases: [
                Arc::new(CirclingPhase),
                Arc::new(StrafingPhase::default()),
                Arc::new(ChargingPhase),
                Arc::new(FlyToPortalPhase),
                Arc::new(LandingApproachPhase::default()),
                Arc::new(LandingPhase),
                Arc::new(SitAttackingPhase),
                Arc::new(SitBreathingPhase),
                Arc::new(TakingOffPhase::default()),
                Arc::new(HoveringPhase),
                Arc::new(DyingPhase),
                Arc::new(SitScanningPhase),
            ],
        }
    }

    #[must_use]
    pub fn get_phase(&self, phase_type: EnderDragonPhase) -> Arc<dyn Phase> {
        self.phases[phase_type as usize].clone()
    }
}

#[cfg(test)]
mod tests {
    use super::{EnderDragonPhase, PhaseManager, default_turn_speed};
    use pumpkin_util::math::vector3::Vector3;

    #[test]
    fn default_turn_speed_matches_observed_hover_turns() {
        for (velocity, observed_yaw) in [
            (Vector3::new(0.0, 0.0, 0.0), -3.5f32),
            (Vector3::new(0.5, 0.0, 0.0), -1.555_555_7),
            (Vector3::new(1.0, 0.0, 0.0), -0.875),
            (Vector3::new(3.0, 0.0, 4.0), -0.097_222_23),
        ] {
            // Fresh dragons facing away from their target clamp yaw error to -50.
            let yaw = -50.0 * default_turn_speed(velocity) * 0.1;
            assert!((yaw - observed_yaw).abs() < 1.0e-6);
            let vertical = Vector3::new(-velocity.x, 10.0, -velocity.z);
            assert_eq!(default_turn_speed(velocity), default_turn_speed(vertical));
        }
    }

    #[test]
    fn default_turn_speed_caps_only_the_first_speed_factor() {
        for (speed, expected) in [(39.0, 0.000_437_5), (79.0, 0.000_218_75)] {
            assert!((default_turn_speed(Vector3::new(speed, 0.0, 0.0)) - expected).abs() < 1.0e-9);
        }
    }

    #[test]
    fn saved_vanilla_phase_ids_select_the_corresponding_handler() {
        let manager = PhaseManager::new();
        for (id, phase) in [
            (0, EnderDragonPhase::Circling),
            (2, EnderDragonPhase::LandingApproach),
            (6, EnderDragonPhase::SitScanning),
            (8, EnderDragonPhase::Charging),
            (9, EnderDragonPhase::Dying),
            (10, EnderDragonPhase::Hovering),
        ] {
            assert_eq!(EnderDragonPhase::from_network_id(id), Some(phase));
            assert_eq!(manager.get_phase(phase).get_type(), phase);
            assert_eq!(phase.network_id(), id);
        }
    }

    #[test]
    fn invalid_phase_ids_use_holding_pattern() {
        for id in [i32::MIN, -1, 11, i32::MAX] {
            assert_eq!(
                EnderDragonPhase::from_network_id(id),
                Some(EnderDragonPhase::Circling),
            );
        }
    }
}
