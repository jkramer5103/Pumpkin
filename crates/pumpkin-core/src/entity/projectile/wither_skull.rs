use std::sync::atomic::{AtomicBool, Ordering};

use pumpkin_data::{Block, damage::DamageType, effect::StatusEffect, potion::Effect, tracked_data};
use pumpkin_nbt::compound::NbtCompound;
use pumpkin_util::{Difficulty, math::vector3::Vector3};

use crate::{
    entity::{
        Entity, EntityBase,
        boss::wither::WitherEntity,
        projectile::{ProjectileHit, ThrownItemEntity, fireball::INITIAL_ACCELERATION_POWER},
    },
    server::Server,
    world::ExplosionInteraction,
};

const GRAVITY: f64 = 0.0;

pub struct WitherSkullEntity {
    pub thrown: ThrownItemEntity,
    pub dangerous: AtomicBool,
}

impl WitherSkullEntity {
    #[must_use]
    pub const fn new(entity: Entity) -> Self {
        let thrown = ThrownItemEntity {
            entity,
            owner_id: None,
            collides_with_projectiles: false,
            has_hit: AtomicBool::new(false),
            gravity: GRAVITY,
        };

        Self {
            thrown,
            dangerous: AtomicBool::new(false),
        }
    }

    #[must_use]
    pub fn new_shot(
        entity: Entity,
        shooter: &Entity,
        dangerous: bool,
        direction: Vector3<f64>,
    ) -> Self {
        let thrown = ThrownItemEntity::new(entity, shooter, GRAVITY);
        let speed = INITIAL_ACCELERATION_POWER;
        let vel = direction.normalize().multiply(speed, speed, speed);
        thrown.entity.velocity.store(vel);

        // Vanilla inherits shooter rotation without assigning a separate head yaw.
        thrown.entity.yaw.store(shooter.yaw.load() % 360.0);
        thrown.entity.set_pitch(shooter.pitch.load());

        Self {
            thrown,
            dangerous: AtomicBool::new(dangerous),
        }
    }

    #[must_use]
    pub fn is_dangerous(&self) -> bool {
        self.dangerous.load(Ordering::Relaxed)
    }

    pub fn set_dangerous(&self, dangerous: bool) {
        self.dangerous.store(dangerous, Ordering::Relaxed);
        self.thrown
            .entity
            .set_synced_data(tracked_data::wither_skull::DATA_DANGEROUS, dangerous);
    }
}

impl EntityBase for WitherSkullEntity {
    fn get_block_explosion_resistance(&self, block: &Block, resistance: f32) -> f32 {
        if self.is_dangerous() && WitherEntity::can_destroy(block) {
            resistance.min(0.8)
        } else {
            resistance
        }
    }

    fn get_owner_id(&self) -> Option<i32> {
        self.thrown.owner_id
    }

    fn write_custom_nbt(&self, nbt: &mut NbtCompound) {
        nbt.put_bool("dangerous", self.is_dangerous());
    }

    fn read_custom_nbt(&self, nbt: &NbtCompound) {
        self.set_dangerous(nbt.get_bool("dangerous").unwrap_or(false));
    }

    fn init_data_tracker(&self) {
        let entity = self.get_entity();
        entity.set_synced_data(
            tracked_data::wither_skull::DATA_DANGEROUS,
            self.is_dangerous(),
        );
    }

    fn tick(&self, caller: &dyn EntityBase, _server: &Server) {
        self.thrown.process_tick(caller);
    }

    fn get_entity(&self) -> &Entity {
        self.thrown.get_entity()
    }

    fn get_living_entity(&self) -> Option<&crate::entity::living::LivingEntity> {
        None
    }

    fn cast_any(&self) -> &dyn std::any::Any {
        self
    }

    fn on_hit(&self, hit: ProjectileHit) {
        let world = self.get_entity().world.load();

        if let ProjectileHit::Entity { ref entity, .. } = hit {
            let difficulty = world.level_info.load().difficulty;

            let owner = self
                .thrown
                .owner_id
                .and_then(|id| world.get_entity_by_id(id));
            let living_owner = owner.as_ref().and_then(|owner| owner.get_living_entity());
            let damaged = if living_owner.is_some() {
                entity.damage(entity.as_ref(), 8.0, DamageType::WITHER_SKULL)
            } else {
                entity.damage(entity.as_ref(), 5.0, DamageType::MAGIC)
            };

            // Living entities remain in the world during their death animation.
            let target_alive = entity.get_entity().is_alive()
                && entity
                    .get_living_entity()
                    .is_none_or(|living| living.health.load() > 0.0);
            if damaged
                && !target_alive
                && let Some(living_owner) = living_owner
                && living_owner.health.load() > 0.0
            {
                living_owner.heal(5.0);
            }

            if let Some(living) = entity.get_living_entity() {
                let duration = match difficulty {
                    Difficulty::Hard => 800,   // 40 seconds
                    Difficulty::Normal => 200, // 10 seconds
                    Difficulty::Easy | Difficulty::Peaceful => 0,
                };

                if duration > 0 {
                    let effect = Effect {
                        effect_type: &StatusEffect::WITHER,
                        duration,
                        amplifier: 1,
                        ambient: false,
                        show_particles: true,
                        show_icon: true,
                        blend: true,
                    };
                    if let Some(player) = entity.get_player() {
                        player.add_effect(effect);
                    } else {
                        living.add_effect(effect);
                    }
                }
            }
        }

        let hit_pos = hit.hit_pos();
        world.explode_with_source(hit_pos, 1.0, ExplosionInteraction::Mob, self);
    }
}
