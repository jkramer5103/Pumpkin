use super::EnderDragonPhase;
use crate::entity::{
    Entity, area_effect_cloud::AreaEffectCloudEntity, boss::ender_dragon::EnderDragonEntity,
};
use pumpkin_data::entity::EntityType;
use pumpkin_util::math::vector3::Vector3;

const WARMUP_TIME: i32 = 10;
const FLAME_DURATION: i32 = 200;

pub struct SitBreathingPhase;

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

        if *timer >= FLAME_DURATION {
            *timer = 0;
            drop(timer);
            dragon.set_phase(EnderDragonPhase::SitAttacking);
            return;
        }
        drop(timer);

        let timer_val = *dragon
            .breathing_timer
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if timer_val == WARMUP_TIME {
            let entity = &dragon.mob_entity.living_entity.entity;
            let pos = entity.pos.load();
            let yaw = entity.yaw.load().to_radians() as f64;
            let world = entity.world.load();

            // Spawn the lingering cloud at the dragon's head position
            let offset = Vector3::new(-yaw.sin() * 2.0, 0.5, yaw.cos() * 2.0);
            let cloud_pos = pos.add(&offset);

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
                FLAME_DURATION, // duration after the cloud's wait time
                5.0,            // radius
                20,             // reapplication delay
                20,             // wait time
                0.0,            // radius on use
                0,              // duration on use
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
