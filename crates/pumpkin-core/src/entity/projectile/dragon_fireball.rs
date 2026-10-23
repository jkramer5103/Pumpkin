use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

use crossbeam::atomic::AtomicCell;
use pumpkin_data::{
    effect::StatusEffect, entity::EntityType, game_event::GameEvent, item::Item,
    item_stack::ItemStack, particle::Particle, world::WorldEvent,
};
use pumpkin_nbt::compound::NbtCompound;
use pumpkin_util::math::{vector3::Vector3, wrap_degrees};
use pumpkin_world::clip::{ClipBlock, ClipContext, ClipFluid};
use uuid::Uuid;

use super::{ProjectileHit, calculate_ray_intersection};
use crate::{
    entity::{Entity, EntityBase, area_effect_cloud::AreaEffectCloudEntity},
    server::Server,
};

const INITIAL_ACCELERATION_POWER: f64 = 0.1;
const SPLASH_RANGE: f64 = 4.0;
const CLOUD_DURATION: i32 = 600;
const CLOUD_RADIUS: f32 = 3.0;
const CLOUD_FINAL_RADIUS: f32 = 7.0;

pub struct DragonFireballEntity {
    entity: Entity,
    owner: AtomicCell<Option<Uuid>>,
    left_owner: AtomicBool,
    has_been_shot: AtomicBool,
    acceleration_power: AtomicCell<f64>,
}

impl DragonFireballEntity {
    pub const fn new(entity: Entity) -> Self {
        Self {
            entity,
            owner: AtomicCell::new(None),
            left_owner: AtomicBool::new(false),
            has_been_shot: AtomicBool::new(false),
            acceleration_power: AtomicCell::new(INITIAL_ACCELERATION_POWER),
        }
    }

    pub fn new_shot(entity: Entity, owner: &Entity, direction: Vector3<f64>) -> Self {
        let projectile = Self::new(entity);
        projectile.owner.store(Some(owner.entity_uuid));
        let velocity = direction.normalize() * INITIAL_ACCELERATION_POWER;
        projectile.entity.velocity.store(velocity);
        projectile
    }

    fn flight_velocity(velocity: Vector3<f64>, acceleration: f64, in_water: bool) -> Vector3<f64> {
        // AbstractHurtingProjectile applies inertia once, before its collision sweep.
        let inertia = f64::from(if in_water { 0.8f32 } else { 0.95f32 });
        (velocity + velocity.normalize() * acceleration) * inertia
    }

    fn owner(&self) -> Option<Arc<dyn EntityBase>> {
        self.owner
            .load()
            .and_then(|id| self.entity.world.load().get_entity_by_uuid(id))
    }

    fn can_hit(&self, candidate: &dyn EntityBase) -> bool {
        let entity = candidate.get_entity();
        entity.entity_id != self.entity.entity_id
            && entity.is_alive()
            && candidate
                .get_living_entity()
                .is_none_or(|living| living.health.load() > 0.0)
            && !candidate.is_spectator()
            && !entity.no_physics.load(Ordering::Relaxed)
            && (candidate.get_living_entity().is_some() || candidate.can_hit())
            && (self.left_owner.load(Ordering::Relaxed)
                || self.owner.load() != Some(entity.entity_uuid))
    }

    fn impact(&self) {
        let world = self.entity.world.load();
        let pos = self.entity.pos.load();
        let candidates = world.get_all_at_box(&self.entity.bounding_box.load().expand(
            SPLASH_RANGE,
            2.0,
            SPLASH_RANGE,
        ));
        let cloud_pos = candidates
            .iter()
            .find_map(|candidate| {
                (candidate.get_living_entity().is_some()
                    && pos.squared_distance_to_vec(&candidate.get_entity().pos.load())
                        < SPLASH_RANGE * SPLASH_RANGE)
                    .then(|| candidate.get_entity().pos.load())
            })
            .unwrap_or(pos);
        let cloud = AreaEffectCloudEntity::create(
            Entity::new(world.clone(), cloud_pos, &EntityType::AREA_EFFECT_CLOUD),
            ItemStack::new(0, &Item::DRAGON_BREATH),
            vec![(&StatusEffect::INSTANT_DAMAGE, 1, 1, false, true, true)],
            CLOUD_DURATION,
            CLOUD_RADIUS,
            20,
            20,
            0.0,
            0,
        );
        if let Some(cloud) = cloud.cast_any().downcast_ref::<AreaEffectCloudEntity>() {
            if let Some(owner) = self.owner()
                && let Some(living) = owner.get_living_entity()
            {
                cloud.set_owner(living);
            }
            cloud.set_custom_particle(Particle::DragonBreath, Box::new(1.0f32.to_be_bytes()));
            *cloud
                .radius_on_tick
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) =
                (CLOUD_FINAL_RADIUS - CLOUD_RADIUS) / CLOUD_DURATION as f32;
        }
        world.sync_world_event(
            WorldEvent::ParticlesDragonFireballSplash,
            self.entity.block_pos.load(),
            if self.entity.is_silent() { -1 } else { 1 },
        );
        world.spawn_entity(cloud);
        self.entity.remove();
    }
}

impl EntityBase for DragonFireballEntity {
    fn get_entity(&self) -> &Entity {
        &self.entity
    }

    fn get_living_entity(&self) -> Option<&crate::entity::living::LivingEntity> {
        None
    }

    fn cast_any(&self) -> &dyn std::any::Any {
        self
    }

    fn get_owner_id(&self) -> Option<i32> {
        self.owner().map(|owner| owner.get_entity().entity_id)
    }

    fn write_custom_nbt(&self, nbt: &mut NbtCompound) {
        if let Some(owner) = self.owner.load() {
            nbt.put_uuid("Owner", owner);
        }
        if self.left_owner.load(Ordering::Relaxed) {
            nbt.put_bool("LeftOwner", true);
        }
        nbt.put_bool("HasBeenShot", self.has_been_shot.load(Ordering::Relaxed));
        nbt.put_double("acceleration_power", self.acceleration_power.load());
    }

    fn read_custom_nbt(&self, nbt: &NbtCompound) {
        self.owner.store(nbt.get_uuid("Owner"));
        self.left_owner.store(
            nbt.get_bool("LeftOwner").unwrap_or(false),
            Ordering::Relaxed,
        );
        self.has_been_shot.store(
            nbt.get_bool("HasBeenShot").unwrap_or(false),
            Ordering::Relaxed,
        );
        self.acceleration_power.store(
            nbt.get_double("acceleration_power")
                .unwrap_or(INITIAL_ACCELERATION_POWER),
        );
    }

    #[expect(clippy::too_many_lines)]
    fn tick(&self, caller: &dyn EntityBase, server: &Server) {
        let world = self.entity.world.load();
        let velocity = Self::flight_velocity(
            self.entity.velocity.load(),
            self.acceleration_power.load(),
            self.entity.touching_water.load(Ordering::Relaxed),
        );
        self.entity.velocity.store(velocity);
        self.entity.velocity_dirty.store(true, Ordering::Relaxed);
        let owner = self.owner();
        if owner
            .as_ref()
            .is_some_and(|owner| owner.get_entity().is_removed())
            || !world.is_loaded(&self.entity.block_pos.load())
        {
            self.entity.remove();
            return;
        }
        if !self.left_owner.load(Ordering::Relaxed) {
            let sweep = self
                .entity
                .bounding_box
                .load()
                .expand_towards(velocity.x, velocity.y, velocity.z)
                .expand_all(1.0);
            if owner
                .as_ref()
                .is_none_or(|owner| !sweep.intersects(&owner.get_entity().bounding_box.load()))
            {
                self.left_owner.store(true, Ordering::Relaxed);
            }
        }
        let start = self.entity.pos.load();
        let end = start + velocity;
        let block = world.clip(&ClipContext::new(
            start,
            end,
            ClipBlock::Collider,
            ClipFluid::None,
        ));
        let mut hit = (!block.is_miss).then_some(ProjectileHit::Block {
            pos: block.block_pos,
            face: block.direction,
            hit_pos: block.location,
            normal: Vector3::new(0.0, 0.0, 0.0),
        });
        let mut distance = if block.is_miss {
            f64::INFINITY
        } else {
            start.squared_distance_to_vec(&block.location)
        };
        let search = self
            .entity
            .bounding_box
            .load()
            .expand_towards(velocity.x, velocity.y, velocity.z)
            .expand_all(1.0);
        // ProjectileUtil's entity margin grows with projectile age, up to 0.3.
        let margin = f64::from(
            ((self.entity.age.load(Ordering::Relaxed) - 1 - 2) as f32 / 20.0).clamp(0.0, 0.3),
        );
        for candidate in world.get_all_at_box(&search) {
            if !self.can_hit(candidate.as_ref()) {
                continue;
            }
            if let Some(t) = calculate_ray_intersection(
                &start,
                &velocity,
                &candidate
                    .get_entity()
                    .bounding_box
                    .load()
                    .expand_all(margin),
            ) {
                let hit_pos = start + velocity * t;
                let candidate_distance = start.squared_distance_to_vec(&hit_pos);
                if candidate_distance < distance {
                    distance = candidate_distance;
                    hit = Some(ProjectileHit::Entity {
                        entity: candidate,
                        hit_pos,
                        normal: Vector3::new(0.0, 0.0, 0.0),
                    });
                }
            }
        }
        if velocity.length_squared() != 0.0 {
            let yaw = velocity.z.atan2(velocity.x).to_degrees() as f32 + 90.0;
            let pitch = velocity.horizontal_length().atan2(velocity.y).to_degrees() as f32 - 90.0;
            self.entity.set_rotation(
                self.entity.yaw.load() + 0.2 * wrap_degrees(yaw - self.entity.yaw.load()),
                self.entity.pitch.load() + 0.2 * wrap_degrees(pitch - self.entity.pitch.load()),
            );
        }
        self.entity
            .set_pos(hit.as_ref().map_or(end, ProjectileHit::hit_pos));
        self.entity.tick(caller, server);
        if !self.has_been_shot.swap(true, Ordering::Relaxed) {
            world.emit_game_event(GameEvent::ProjectileShoot.name(), self.entity.pos.load());
        }
        if let Some(hit) = hit {
            if let ProjectileHit::Block { pos, hit_pos, .. } = &hit {
                world.block_registry.on_projectile_hit(
                    world.get_block(pos),
                    &world,
                    caller,
                    pos,
                    world.get_block_state(pos),
                    hit_pos,
                    server,
                );
            }
            world.emit_game_event(GameEvent::ProjectileLand.name(), self.entity.pos.load());
            // Returning to the owner does not detonate a dragon fireball.
            if !matches!(&hit, ProjectileHit::Entity { entity, .. } if self.owner.load() == Some(entity.get_entity().entity_uuid))
            {
                self.impact();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::DragonFireballEntity;
    use pumpkin_util::math::vector3::Vector3;

    #[test]
    fn dragon_fireball_accelerates_before_moving_without_thrown_item_drag() {
        let mut velocity = Vector3::new(0.1, 0.0, 0.0);
        let mut x = 0.0;
        // Official AbstractHurtingProjectile, air inertia is a widened Java float.
        for (expected_velocity, expected_x) in [
            (0.1899999976158142, 0.1899999976158142),
            (0.27549999427795413, 0.46549999189376834),
            (0.35672499008774766, 0.822224981981516),
        ] {
            velocity = DragonFireballEntity::flight_velocity(velocity, 0.1, false);
            x += velocity.x;
            assert!((velocity.x - expected_velocity).abs() < 1e-14);
            assert!((x - expected_x).abs() < 1e-14);
            assert_eq!(velocity.y, 0.0);
            assert_eq!(velocity.z, 0.0);
        }
        assert_eq!(
            DragonFireballEntity::flight_velocity(Vector3::new(0.0, 0.0, 0.0), 0.1, false),
            Vector3::new(0.0, 0.0, 0.0)
        );
    }
}
