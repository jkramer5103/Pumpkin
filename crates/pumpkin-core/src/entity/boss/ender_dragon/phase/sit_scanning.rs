use super::{EnderDragonPhase, Phase};
use crate::entity::{
    EntityBase, ai::target_predicate::TargetPredicate, boss::ender_dragon::EnderDragonEntity,
};
use pumpkin_util::math::{vector3::Vector3, wrap_degrees_f64};

const SITTING_SCANNING_IDLE_TICKS: i32 = 100;
const SITTING_ATTACK_Y_VIEW_RANGE: f64 = 10.0;
const SITTING_ATTACK_VIEW_RANGE: f64 = 20.0;
const SITTING_CHARGE_VIEW_RANGE: f64 = 150.0;

pub struct SitScanningPhase;

impl SitScanningPhase {
    fn turn_toward(
        pos: Vector3<f64>,
        head_pos: Vector3<f64>,
        target: Vector3<f64>,
        yaw: f32,
        yaw_rot_accel: &mut f32,
    ) -> f32 {
        let aim = Vector3::new(target.x - pos.x, 0.0, target.z - pos.z).normalize();
        let yaw_radians = yaw.to_radians();
        let dir = Vector3::new(
            f64::from(yaw_radians.sin()),
            0.0,
            -f64::from(yaw_radians.cos()),
        )
        .normalize();
        let dot = dir.dot(&aim) as f32;
        let angle = dot.acos().to_degrees() + 0.5;
        if angle > 10.0 {
            let xd = target.x - head_pos.x;
            let zd = target.z - head_pos.z;
            let y_rot_delta = wrap_degrees_f64(180.0 - xd.atan2(zd).to_degrees() - f64::from(yaw))
                .clamp(-100.0, 100.0);
            *yaw_rot_accel *= 0.8;
            let rot_speed = xd.hypot(zd) as f32 + 1.0;
            let dist = rot_speed.min(40.0);
            *yaw_rot_accel += y_rot_delta as f32 * (0.7 / dist / rot_speed);
            return yaw + *yaw_rot_accel;
        }
        yaw
    }
}

impl Phase for SitScanningPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::SitScanning
    }

    fn is_sitting(&self) -> bool {
        true
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        *dragon
            .scanning_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let scanning_time = {
            let mut time = dragon
                .scanning_time
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            *time += 1;
            *time
        };
        let entity = dragon.get_entity();
        let world = entity.world.load();
        let pos = entity.pos.load();
        let scan_targeting =
            TargetPredicate::create_attackable().set_base_max_distance(SITTING_ATTACK_VIEW_RANGE);
        let attack_target = world.get_nearest_player(pos, SITTING_ATTACK_VIEW_RANGE, |player| {
            (player.get_entity().pos.load().y - pos.y).abs() <= SITTING_ATTACK_Y_VIEW_RANGE
                && scan_targeting.test(&world, Some(dragon), player.as_ref())
        });

        if let Some(target) = attack_target {
            if scanning_time > 25 {
                dragon.set_phase(EnderDragonPhase::SitAttacking);
            } else {
                let mut yaw_rot_accel = dragon
                    .yaw_rot_accel
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                entity.yaw.store(Self::turn_toward(
                    pos,
                    dragon.parts[0].entity.pos.load(),
                    target.get_entity().pos.load(),
                    entity.yaw.load(),
                    &mut yaw_rot_accel,
                ));
            }
        } else if scanning_time >= SITTING_SCANNING_IDLE_TICKS {
            let charge_targeting = TargetPredicate::create_attackable()
                .set_base_max_distance(SITTING_CHARGE_VIEW_RANGE);
            let target = world.get_nearest_player(pos, SITTING_CHARGE_VIEW_RANGE, |player| {
                charge_targeting.test(&world, Some(dragon), player.as_ref())
            });
            dragon.set_phase(EnderDragonPhase::TakingOff);
            if let Some(target) = target {
                *dragon
                    .target_player
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner) =
                    Some(target.gameprofile.id);
                dragon.set_phase(EnderDragonPhase::Charging);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::SitScanningPhase;
    use pumpkin_util::math::vector3::Vector3;

    #[test]
    fn scanning_turn_keeps_aligned_heading_and_uses_head_relative_distance() {
        let pos = Vector3::new(0.0, 100.0, 0.0);
        let head = Vector3::new(0.0, 99.0, -6.5);
        let mut accel = 0.3;
        assert_eq!(
            SitScanningPhase::turn_toward(
                pos,
                head,
                Vector3::new(0.0, 100.0, -15.0),
                0.0,
                &mut accel,
            ),
            0.0,
        );
        assert_eq!(accel, 0.3);

        let turned = SitScanningPhase::turn_toward(
            pos,
            head,
            Vector3::new(15.0, 100.0, 0.0),
            0.0,
            &mut accel,
        );
        assert!((turned - 0.4726002).abs() < 0.00001);
        assert_eq!(turned, accel);
    }
}
