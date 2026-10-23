use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::{
    entity::{Entity, EntityBase},
    server::Server,
};
use crossbeam::atomic::AtomicCell;
use pumpkin_data::effect::StatusEffect;
use pumpkin_nbt::compound::NbtCompound;
use pumpkin_util::math::boundingbox::BoundingBox;
use pumpkin_util::math::vector3::Vector3;
use uuid::Uuid;

type EffectEntry = (&'static StatusEffect, i32, u8, bool, bool, bool);
use pumpkin_data::item_stack::ItemStack;

#[derive(Clone)]
struct ParticleMeta {
    particle_id: pumpkin_protocol::codec::var_int::VarInt,
    data: Box<[u8]>,
}

impl pumpkin_protocol::java::client::play::MetadataSerializer for ParticleMeta {
    fn write_metadata(
        &self,
        writer: &mut impl std::io::Write,
        _version: &pumpkin_util::version::JavaMinecraftVersion,
    ) -> Result<(), pumpkin_protocol::ser::WritingError> {
        use pumpkin_protocol::ser::NetworkWriteExt;
        writer.write_var_int(&self.particle_id)?;
        writer.write_slice(&self.data)
    }
}

/// The effect cloud entity that is spawned where a lingering potion lands.
pub struct AreaEffectCloudEntity {
    pub entity: Entity,
    owner: AtomicCell<Option<Uuid>>,
    /// Stored potion item stack (may be empty) to read effects from.
    pub item_stack: Mutex<ItemStack>,
    custom_particle: Mutex<Option<ParticleMeta>>,
    /// Active potion effects as tuples: (`StatusEffect`, `duration_ticks`, `amplifier`, `ambient`, `show_particles`, `show_icon`)
    pub effects: Mutex<Vec<EffectEntry>>,
    pub radius: Mutex<f32>,
    pub duration: Mutex<i32>,
    pub age: Mutex<i32>,
    /// ticks between reapplications to the same entity
    pub reapplication_delay: Mutex<i32>,
    /// map of `entity_id` -> cloud age when that entity can be affected again
    pub reapplication_map: Mutex<HashMap<i32, i32>>,
    /// linear radius change per tick
    pub radius_on_tick: Mutex<f32>,
    /// radius change when an entity is affected
    pub radius_on_use: Mutex<f32>,
    /// duration change (ticks) when an entity is affected
    pub duration_on_use: Mutex<i32>,
    /// ticks to wait before the cloud becomes active and applies effects (grace period)
    pub wait_time: Mutex<i32>,
}

impl AreaEffectCloudEntity {
    pub fn set_owner(&self, owner: &crate::entity::living::LivingEntity) {
        self.owner.store(Some(owner.entity.entity_uuid));
    }

    fn owner(&self) -> Option<Arc<dyn EntityBase>> {
        self.owner
            .load()
            .and_then(|id| self.entity.world.load().get_entity_by_uuid(id))
            .filter(|owner| owner.get_living_entity().is_some())
    }

    fn tick_victims(victims: &mut HashMap<i32, i32>, age: i32) -> bool {
        if age % 5 != 0 {
            return false;
        }
        victims.retain(|_, next_application| age < *next_application);
        true
    }

    const fn has_expired(age: i32, wait_time: i32, duration: i32) -> bool {
        duration != -1 && age - wait_time >= duration
    }

    fn effect_bounds(pos: Vector3<f64>, radius: f64) -> BoundingBox {
        let height = f64::from(pumpkin_data::entity::EntityType::AREA_EFFECT_CLOUD.dimension[1]);
        BoundingBox::new(
            Vector3::new(pos.x - radius, pos.y, pos.z - radius),
            Vector3::new(pos.x + radius, pos.y + height, pos.z + radius),
        )
    }

    #[allow(clippy::new_ret_no_self)]
    pub fn new(entity: Entity) -> Arc<dyn EntityBase> {
        entity
            .no_physics
            .store(true, std::sync::atomic::Ordering::Relaxed);
        let cloud = Self {
            entity,
            owner: AtomicCell::new(None),
            item_stack: Mutex::new(ItemStack::new(0, &pumpkin_data::item::Item::GLASS_BOTTLE)),
            custom_particle: Mutex::new(None),
            effects: Mutex::new(Vec::new()),
            radius: Mutex::new(3.0),
            duration: Mutex::new(600), // default for lingering potions
            age: Mutex::new(0),
            reapplication_delay: Mutex::new(20),
            reapplication_map: Mutex::new(HashMap::new()),
            radius_on_tick: Mutex::new(-3.0 / 600.0), // default for lingering potions
            radius_on_use: Mutex::new(0.0),
            duration_on_use: Mutex::new(0),
            wait_time: Mutex::new(20),
        };

        Arc::new(cloud)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn create(
        entity: Entity,
        item_stack: ItemStack,
        effects_in: Vec<EffectEntry>,
        duration_in: i32,
        radius_in: f32,
        reapplication_delay_in: i32,
        wait_time_in: i32,
        radius_on_use_in: f32,
        duration_on_use_in: i32,
    ) -> Arc<dyn EntityBase> {
        entity
            .no_physics
            .store(true, std::sync::atomic::Ordering::Relaxed);
        let cloud = Self {
            entity,
            owner: AtomicCell::new(None),
            item_stack: Mutex::new(item_stack),
            custom_particle: Mutex::new(None),
            effects: Mutex::new(effects_in),
            radius: Mutex::new(radius_in),
            duration: Mutex::new(duration_in),
            age: Mutex::new(0),
            reapplication_delay: Mutex::new(reapplication_delay_in),
            reapplication_map: Mutex::new(HashMap::new()),
            radius_on_tick: Mutex::new(-radius_in / (duration_in as f32).max(1.0)),
            radius_on_use: Mutex::new(radius_on_use_in),
            duration_on_use: Mutex::new(duration_on_use_in),
            wait_time: Mutex::new(wait_time_in),
        };

        Arc::new(cloud)
    }

    pub fn set_custom_particle(&self, particle: pumpkin_data::particle::Particle, data: Box<[u8]>) {
        let meta = ParticleMeta {
            particle_id: pumpkin_protocol::codec::var_int::VarInt(particle as i32),
            data,
        };
        *self
            .custom_particle
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = Some(meta.clone());
        self.entity.set_synced_data(
            pumpkin_data::tracked_data::area_effect_cloud::PARTICLE,
            meta,
        );
    }
}

impl EntityBase for AreaEffectCloudEntity {
    fn write_custom_nbt(&self, nbt: &mut NbtCompound) {
        if let Some(owner) = self.owner.load() {
            nbt.put_uuid("Owner", owner);
        }
    }

    fn read_custom_nbt(&self, nbt: &NbtCompound) {
        self.owner.store(nbt.get_uuid("Owner"));
    }

    fn init_data_tracker(&self) {
        // Send initial radius and particle (color) so clients render correctly
        let radius = *self
            .radius
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);

        // Compute particle color
        let stack = self
            .item_stack
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone();
        let effects = self
            .effects
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone();

        // Use ARGB format
        let mut color: i32 = (0xFFi32 << 24) | 0x385dc6; // default water-like color

        if let Some(pc) =
            stack.get_data_component::<pumpkin_data::data_component_impl::PotionContentsImpl>()
        {
            if let Some(c) = pc.custom_color {
                color = c | (0xFFi32 << 24);
            } else if !effects.is_empty() {
                let mut r_sum = 0.0f32;
                let mut g_sum = 0.0f32;
                let mut b_sum = 0.0f32;
                let count = effects.len() as f32;
                for (eff, _, _, _, _, _) in &effects {
                    let c = eff.color;
                    r_sum += ((c >> 16) & 0xFF) as f32;
                    g_sum += ((c >> 8) & 0xFF) as f32;
                    b_sum += (c & 0xFF) as f32;
                }
                let r = (r_sum / count) as i32;
                let g = (g_sum / count) as i32;
                let b = (b_sum / count) as i32;
                color = (0xFFi32 << 24) | (r << 16) | (g << 8) | b;
            }
        } else if !effects.is_empty() {
            let mut r_sum = 0.0f32;
            let mut g_sum = 0.0f32;
            let mut b_sum = 0.0f32;
            let count = effects.len() as f32;
            for (eff, _, _, _, _, _) in &effects {
                let c = eff.color;
                r_sum += ((c >> 16) & 0xFF) as f32;
                g_sum += ((c >> 8) & 0xFF) as f32;
                b_sum += (c & 0xFF) as f32;
            }
            let r = (r_sum / count) as i32;
            let g = (g_sum / count) as i32;
            let b = (b_sum / count) as i32;
            color = (0xFFi32 << 24) | (r << 16) | (g << 8) | b;
        }

        // Build raw particle option bytes for ENTITY_EFFECT
        let data_bytes = color.to_be_bytes();

        let meta = self
            .custom_particle
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone()
            .unwrap_or_else(|| ParticleMeta {
                particle_id: pumpkin_protocol::codec::var_int::VarInt(
                    pumpkin_data::particle::Particle::EntityEffect as i32,
                ),
                data: Box::new(data_bytes),
            });

        self.entity.set_synced_data(
            pumpkin_data::tracked_data::area_effect_cloud::PARTICLE,
            meta,
        );

        self.entity.set_synced_data(
            pumpkin_data::tracked_data::area_effect_cloud::RADIUS,
            radius,
        );

        // Initial waiting flag
        let wait_time = *self
            .wait_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let is_waiting = 0 < wait_time;
        self.entity.set_synced_data(
            pumpkin_data::tracked_data::area_effect_cloud::WAITING,
            is_waiting,
        );
    }

    #[allow(clippy::too_many_lines)]
    #[allow(clippy::semicolon_outside_block)]
    fn tick(&self, caller: &dyn EntityBase, _server: &Server) {
        // Age & duration handling
        {
            let mut age = self
                .age
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            *age += 1;
            let duration = *self
                .duration
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            let wait_time = *self
                .wait_time
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if Self::has_expired(*age, wait_time, duration) {
                // Remove old entities
                self.entity.remove();
                return;
            }
        }

        // Get current age and waiting period
        let age = *self
            .age
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let wait_time = *self
            .wait_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);

        // When the waiting period ends, notify clients so they render full particles
        if age == wait_time && wait_time > 0 {
            self.entity.set_synced_data(
                pumpkin_data::tracked_data::area_effect_cloud::WAITING,
                false,
            );
        }

        if age < wait_time {
            // Respect waiting/grace period
            return;
        }

        // Update radius
        {
            let mut radius = self
                .radius
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            let delta = *self
                .radius_on_tick
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            *radius += delta;
            let current_radius = *radius;
            if current_radius <= 0.0 {
                self.entity.remove();
                return;
            }

            // Send new radius
            drop(radius);
            self.entity.set_synced_data(
                pumpkin_data::tracked_data::area_effect_cloud::RADIUS,
                current_radius,
            );
        }

        // Vanilla samples victims every five ticks, using absolute age deadlines.
        {
            let mut map = self
                .reapplication_map
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if !Self::tick_victims(&mut map, age) {
                return;
            }
        }

        // Apply effects to nearby entities if eligible
        let pos = self.entity.pos.load();
        let r = *self
            .radius
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) as f64;
        let aabb = Self::effect_bounds(pos, r);
        let world = self.entity.world.load();

        let mut candidates = world.get_entities_at_box(&aabb);
        let players = world.get_players_at_box(&aabb);
        for p in players {
            candidates.push(p.clone() as Arc<dyn EntityBase>);
        }

        let owner = self.owner();
        for cand in candidates {
            let cand_clone = cand.clone();

            // Skip self and other `AreaEffectCloud` entities
            if cand_clone.get_entity().entity_id == self.get_entity().entity_id {
                continue;
            }
            if *cand_clone.get_entity().entity_type
                == pumpkin_data::entity::EntityType::AREA_EFFECT_CLOUD
            {
                continue;
            }

            // Determine candidate id early
            let ent_id = cand_clone.get_entity().entity_id;

            {
                let map = self
                    .reapplication_map
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                if map.contains_key(&ent_id) {
                    continue;
                }
            }

            let radius_f = *self
                .radius
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                as f64;
            let pos_e = cand_clone.get_entity().pos.load();
            let dist_sq = pos.squared_distance_to_vec_xz(pos_e);
            if dist_sq > radius_f * radius_f {
                continue;
            }

            let scale = 1.0f32 - (dist_sq.sqrt() as f32 / radius_f as f32);

            // Decide whether this contact will actually apply an effect
            let effs_clone = self
                .effects
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .clone();
            let mut will_apply = false;

            // Only living entities can receive effects
            if let Some(living_ref) = cand_clone.get_living_entity() {
                for (eff, _, _, _, _, _) in &effs_clone {
                    // Instant effects always apply
                    let is_instant = eff.id
                        == pumpkin_data::effect::StatusEffect::INSTANT_DAMAGE.id
                        || eff.id == pumpkin_data::effect::StatusEffect::INSTANT_HEALTH.id;
                    if is_instant {
                        will_apply = true;
                        break;
                    }

                    // Only apply if entity does not already have that effect
                    if !living_ref.has_effect(eff) {
                        will_apply = true;
                        break;
                    }
                }
            }

            // If nothing would be applied, skip
            if !will_apply {
                continue;
            }

            // Apply the cloud as the direct source and its living owner as the cause.
            if let Some(living) = cand_clone.get_living_entity() {
                crate::item::potion::PotionContents::apply_effects_with_context(
                    living,
                    effs_clone,
                    scale,
                    crate::item::potion::PotionApplicationSource::AreaEffectCloud,
                    Some(caller),
                    owner.as_deref(),
                );
            }

            // Set reapplication delay for this entity
            let delay = *self
                .reapplication_delay
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            self.reapplication_map
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .insert(ent_id, age + delay);

            // Apply radius-on-use (shrink)
            let radius_on_use = *self
                .radius_on_use
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if radius_on_use != 0.0 {
                let mut radius_lock = self
                    .radius
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                *radius_lock += radius_on_use;
                let current_radius = *radius_lock;
                if current_radius < 0.5 {
                    drop(radius_lock);
                    self.entity.remove();
                    return;
                }
                drop(radius_lock);

                // Send updated radius to clients
                self.entity.set_synced_data(
                    pumpkin_data::tracked_data::area_effect_cloud::RADIUS,
                    current_radius,
                );
            }

            // Apply duration-on-use (shorten lifespan)
            let duration_on_use = *self
                .duration_on_use
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if duration_on_use != 0 {
                let mut duration_lock = self
                    .duration
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                if *duration_lock != -1 {
                    *duration_lock += duration_on_use;
                    if *duration_lock <= 0 {
                        drop(duration_lock);
                        self.entity.remove();
                        return;
                    }
                }
            }
        }
    }

    fn get_entity(&self) -> &Entity {
        &self.entity
    }

    fn get_living_entity(&self) -> Option<&crate::entity::living::LivingEntity> {
        None
    }

    fn cast_any(&self) -> &dyn std::any::Any {
        self
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::AreaEffectCloudEntity;
    use pumpkin_util::math::{boundingbox::BoundingBox, vector3::Vector3};

    #[test]
    fn cloud_samples_new_and_returning_victims_on_five_tick_boundaries() {
        // A victim enters an already active cloud at age 21, between samples.
        for (delay, expected) in [(20, vec![25, 45, 65]), (7, vec![25, 35, 45, 55, 65])] {
            let mut victims = HashMap::new();
            let mut contacts = Vec::new();
            for age in 21..=65 {
                if AreaEffectCloudEntity::tick_victims(&mut victims, age)
                    && !victims.contains_key(&1)
                {
                    contacts.push(age);
                    victims.insert(1, age + delay);
                }
            }
            assert_eq!(contacts, expected);
        }
    }

    #[test]
    fn cloud_contact_requires_vertical_hitbox_overlap() {
        let bounds = AreaEffectCloudEntity::effect_bounds(Vector3::new(8.0, 80.0, 3.0), 5.0);
        for (min_y, max_y, expected) in [
            (80.0, 81.3, true),
            (80.5, 81.8, false),
            (82.0, 83.3, false),
            (78.0, 79.3, false),
            (78.7, 80.0, false),
            (79.0, 80.3, true),
        ] {
            let victim =
                BoundingBox::new(Vector3::new(7.5, min_y, 2.5), Vector3::new(8.5, max_y, 3.5));
            assert_eq!(bounds.intersects(&victim), expected, "{min_y}..{max_y}");
        }
    }

    #[test]
    fn cloud_duration_starts_after_wait_time_and_expires_at_the_boundary() {
        // Sitting dragon flames have a 20-tick wait and a 200-tick duration.
        for age in [0, 19, 20, 200, 219] {
            assert!(!AreaEffectCloudEntity::has_expired(age, 20, 200));
        }
        for age in [220, 221, 600] {
            assert!(AreaEffectCloudEntity::has_expired(age, 20, 200));
        }
        assert!(!AreaEffectCloudEntity::has_expired(19, 0, 20));
        assert!(AreaEffectCloudEntity::has_expired(20, 0, 20));
        assert!(!AreaEffectCloudEntity::has_expired(21, 20, 2));
        assert!(AreaEffectCloudEntity::has_expired(22, 20, 2));
    }

    #[test]
    fn zero_duration_cloud_expires_when_wait_time_ends() {
        assert!(!AreaEffectCloudEntity::has_expired(19, 20, 0));
        assert!(AreaEffectCloudEntity::has_expired(20, 20, 0));
    }

    #[test]
    fn indefinite_cloud_does_not_expire_from_age() {
        for age in [0, 19, 20, 220, 600, i32::MAX] {
            assert!(!AreaEffectCloudEntity::has_expired(age, 20, -1));
            assert!(!AreaEffectCloudEntity::has_expired(age, 0, -1));
        }
    }
}
