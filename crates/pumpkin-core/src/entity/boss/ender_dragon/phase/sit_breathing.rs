use super::EnderDragonPhase;
use crate::entity::{
    Entity, area_effect_cloud::AreaEffectCloudEntity, boss::ender_dragon::EnderDragonEntity,
};
use pumpkin_data::entity::EntityType;
use pumpkin_util::math::position::BlockPos;
use pumpkin_util::math::vector3::Vector3;

const WARMUP_TIME: i32 = 10;
const FLAME_DURATION: i32 = 200;
const SITTING_FLAME_ATTACKS_COUNT: i32 = 4;
const FLAME_RADIUS: f64 = 5.0;

pub struct SitBreathingPhase;

impl SitBreathingPhase {
    const fn next_phase(flame_ticks: i32, flame_count: i32) -> Option<EnderDragonPhase> {
        if flame_ticks < FLAME_DURATION {
            return None;
        }
        Some(if flame_count >= SITTING_FLAME_ATTACKS_COUNT {
            EnderDragonPhase::TakingOff
        } else {
            EnderDragonPhase::SitScanning
        })
    }

    pub fn reset_flame_count(dragon: &EnderDragonEntity) {
        *dragon
            .flame_count
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
    }

    fn flame_position(
        dragon_pos: Vector3<f64>,
        head_pos: Vector3<f64>,
        mut is_empty_block: impl FnMut(BlockPos) -> bool,
    ) -> Vector3<f64> {
        let look =
            Vector3::new(head_pos.x - dragon_pos.x, 0.0, head_pos.z - dragon_pos.z).normalize();
        let x = head_pos.x + look.x * FLAME_RADIUS / 2.0;
        let z = head_pos.z + look.z * FLAME_RADIUS / 2.0;
        // Vanilla's head part is one block tall; start at its vertical midpoint.
        let initial_y = head_pos.y + 0.5;
        let mut y = initial_y;
        while is_empty_block(BlockPos::new(
            x.floor() as i32,
            y.floor() as i32,
            z.floor() as i32,
        )) {
            y -= 1.0;
            // This is vanilla's zero cutoff, independent of the dimension's min Y.
            if y < 0.0 {
                y = initial_y;
                break;
            }
        }
        Vector3::new(x, y.floor() + 1.0, z)
    }
}

impl super::Phase for SitBreathingPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::SitBreathing
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        *dragon
            .breathing_timer
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
        *dragon
            .flame_count
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) += 1;
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    fn end(&self, dragon: &EnderDragonEntity) {
        let flame = dragon
            .flame
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .take();
        if let Some(uuid) = flame
            && let Some(cloud) = dragon
                .mob_entity
                .living_entity
                .entity
                .world
                .load()
                .get_entity_by_uuid(uuid)
        {
            cloud.get_entity().remove();
        }
    }

    fn tick(&self, dragon: &EnderDragonEntity) {
        let mut timer = dragon
            .breathing_timer
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        *timer += 1;

        let flame_count = *dragon
            .flame_count
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if let Some(next_phase) = Self::next_phase(*timer, flame_count) {
            *timer = 0;
            drop(timer);
            dragon.set_phase(next_phase);
            return;
        }
        drop(timer);

        let timer_val = *dragon
            .breathing_timer
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if timer_val == WARMUP_TIME {
            let entity = &dragon.mob_entity.living_entity.entity;
            let world = entity.world.load();
            let cloud_pos = Self::flame_position(
                entity.pos.load(),
                dragon.parts[0].entity.pos.load(),
                |pos| world.get_block_state(&pos).is_air(),
            );

            let cloud_entity =
                Entity::new(world.clone(), cloud_pos, &EntityType::AREA_EFFECT_CLOUD);
            let cloud = AreaEffectCloudEntity::create(
                cloud_entity,
                pumpkin_data::item_stack::ItemStack::new(
                    0,
                    &pumpkin_data::item::Item::DRAGON_BREATH,
                ),
                vec![(
                    &pumpkin_data::effect::StatusEffect::INSTANT_DAMAGE,
                    1,
                    0,
                    false,
                    true,
                    true,
                )],
                FLAME_DURATION,      // duration after the cloud's wait time
                FLAME_RADIUS as f32, // radius
                20,                  // reapplication delay
                20,                  // wait time
                0.0,                 // radius on use
                0,                   // duration on use
            );
            // Sitting dragon flames keep their radius instead of shrinking like potions.
            if let Some(flame) = cloud.cast_any().downcast_ref::<AreaEffectCloudEntity>() {
                *flame
                    .radius_on_tick
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner) = 0.0;
            }
            *dragon
                .flame
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) =
                Some(cloud.get_entity().entity_uuid);
            world.spawn_entity(cloud);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{EnderDragonPhase, SitBreathingPhase};
    use pumpkin_util::math::{position::BlockPos, vector3::Vector3};

    #[test]
    fn fourth_flame_takes_off_only_at_its_completion() {
        for (count, next_phase) in [
            (1, EnderDragonPhase::SitScanning),
            (2, EnderDragonPhase::SitScanning),
            (3, EnderDragonPhase::SitScanning),
            (4, EnderDragonPhase::TakingOff),
            (5, EnderDragonPhase::TakingOff),
        ] {
            assert_eq!(SitBreathingPhase::next_phase(199, count), None);
            assert_eq!(SitBreathingPhase::next_phase(200, count), Some(next_phase));
        }
    }

    #[test]
    fn flame_is_ahead_of_head_and_above_first_non_air_block() {
        let pos = SitBreathingPhase::flame_position(
            Vector3::new(0.5, 100.0, 0.5),
            Vector3::new(0.5, 99.0, -6.0),
            |pos| {
                assert_eq!(pos.0.x, 0);
                assert_eq!(pos.0.z, -9);
                pos.0.y > 79
            },
        );
        assert_eq!(pos, Vector3::new(0.5, 80.0, -8.5));

        let rotated = SitBreathingPhase::flame_position(
            Vector3::new(0.5, 100.0, 0.5),
            Vector3::new(7.0, 99.0, 0.5),
            |pos| pos != BlockPos::new(9, 89, 0),
        );
        assert_eq!(rotated, Vector3::new(9.5, 90.0, 0.5));
    }

    #[test]
    fn empty_column_restores_head_height_before_searching_below_zero() {
        let pos = SitBreathingPhase::flame_position(
            Vector3::new(0.5, 100.0, 0.5),
            Vector3::new(0.5, 99.0, -6.0),
            |pos| {
                assert!(pos.0.y >= 0);
                true
            },
        );
        assert_eq!(pos, Vector3::new(0.5, 100.0, -8.5));
    }

    #[test]
    fn occupied_start_uses_floor_and_does_not_search_downward() {
        let mut sampled = Vec::new();
        let pos = SitBreathingPhase::flame_position(
            Vector3::new(-2.5, 20.0, -2.5),
            Vector3::new(-2.5, 18.75, -9.0),
            |pos| {
                sampled.push(pos);
                false
            },
        );
        assert_eq!(sampled, vec![BlockPos::new(-3, 19, -12)]);
        assert_eq!(pos, Vector3::new(-2.5, 20.0, -11.5));
    }
}
