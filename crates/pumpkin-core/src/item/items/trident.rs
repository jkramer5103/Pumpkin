use std::any::Any;
use std::sync::Arc;
use std::sync::atomic::Ordering;

use crate::enchantment::EnchantmentHelper;
use crate::entity::player::Player;
use crate::entity::projectile::arrow::ArrowPickup;
use crate::entity::projectile::trident::TridentEntity;
use crate::entity::{Entity, EntityBase};
use crate::item::{ItemBehaviour, ItemMetadata};
use pumpkin_data::data_component_impl::EquipmentSlot;
use pumpkin_data::entity::EntityType;
use pumpkin_data::item::Item;
use pumpkin_data::item_stack::ItemStack;
use pumpkin_data::sound::{Sound, SoundCategory};
use pumpkin_protocol::java::client::play::CEntityVelocity;
use pumpkin_util::math::vector3::Vector3;
use pumpkin_util::{GameMode, Hand};

pub struct TridentItem;

impl ItemMetadata for TridentItem {
    fn ids() -> Box<[u16]> {
        [Item::TRIDENT.id].into()
    }
}

impl ItemBehaviour for TridentItem {
    fn normal_use_with_hand(
        &self,
        _item: &Item,
        player: &Player,
        _yaw: f32,
        _pitch: f32,
        hand: Hand,
    ) {
        let stack = player.inventory().get_stack_in_hand(hand);
        if stack.next_damage_will_break()
            || (EnchantmentHelper::modify_trident_spin_attack_strength(&stack, 0.0) > 0.0
                && !player.get_entity().is_in_water_or_rain())
        {
            return;
        }
        player
            .living_entity
            .set_active_hand(hand, stack, Self::USE_DURATION);
    }

    fn on_stopped_using(&self, stack: &ItemStack, player: &Player) {
        let use_ticks = player
            .living_entity
            .item_use_time
            .load(std::sync::atomic::Ordering::Relaxed);
        let use_ticks = Self::USE_DURATION - use_ticks;

        if use_ticks < Self::THROW_THRESHOLD_TIME || stack.next_damage_will_break() {
            return;
        }

        let world = player.world();
        let hand = player
            .living_entity
            .active_hand
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .unwrap_or(Hand::Right);
        let riptide_strength = EnchantmentHelper::modify_trident_spin_attack_strength(stack, 0.0);
        let sound = EnchantmentHelper::pick_trident_sound(stack).unwrap_or(Sound::ItemTridentThrow);

        if riptide_strength > 0.0 {
            if !player.get_entity().is_in_water_or_rain() || player.get_entity().has_vehicle() {
                return;
            }

            if let Some(player_arc) = world.get_player_by_uuid(player.gameprofile.id)
                && let Some(server) = world.server.upgrade()
            {
                let mut event =
                    crate::plugin::api::events::player::player_riptide::PlayerRiptideEvent {
                        player: player_arc,
                        item_name: "trident".to_string(),
                        cancelled: false,
                    };
                server.plugin_manager.fire_blocking(&server, &mut event);
                if event.cancelled {
                    player.living_entity.clear_active_hand();
                    return;
                }
            }
        }

        player.increment_stat(
            pumpkin_data::statistic::StatisticCategory::Used,
            i32::from(Item::TRIDENT.id),
            1,
        );
        player.damage_item_in_slot(&Self::equipment_slot(hand), 1);

        if riptide_strength > 0.0 {
            let (yaw, pitch) = player.rotation();
            let impulse = Self::riptide_impulse(yaw, pitch, riptide_strength);
            let entity = player.get_entity();
            entity.velocity.store(entity.velocity.load() + impulse);
            // The owning Java client predicts the impulse and ground lift itself.
            world.send_to_tracking_players(
                entity,
                &CEntityVelocity::new(entity.entity_id.into(), entity.velocity.load()),
            );
            player.living_entity.start_auto_spin_attack(
                Self::SPIN_ATTACK_TICKS,
                Self::BASE_DAMAGE,
                player.inventory().get_stack_in_hand(hand),
            );
            if entity.on_ground.load(Ordering::Relaxed) {
                let motion = entity.adjust_movement_for_collisions(
                    Vector3::new(0.0, Self::GROUND_LIFT, 0.0),
                    player,
                );
                entity.move_pos(motion);
            }
            world.play_sound(sound, SoundCategory::Players, &player.position());
            player.living_entity.clear_active_hand();
            return;
        }

        // Normal throw - spawn thrown trident
        let thrown_stack = player.inventory().get_stack_in_hand(hand);
        let (yaw, pitch) = player.rotation();
        let entity = Entity::new(world.clone(), player.position(), &EntityType::TRIDENT);
        let trident = TridentEntity::new_shot(
            entity,
            player.get_entity(),
            thrown_stack.clone(),
            if player.gamemode.load() == GameMode::Creative {
                ArrowPickup::CreativeOnly
            } else {
                ArrowPickup::Allowed
            },
        );
        trident.set_velocity_from_rotation(pitch, yaw, 0.0, 2.5, 1.0);
        trident.apply_on_projectile_spawned(&thrown_stack);
        world.spawn_entity(Arc::new(trident));

        world.play_sound(sound, SoundCategory::Players, &player.position());

        if player.gamemode.load() != GameMode::Creative {
            let inventory = player.inventory();
            inventory.set_stack_in_hand(hand, ItemStack::EMPTY.clone());
            let slot = if hand == Hand::Right {
                inventory.get_selected_slot() as usize
            } else {
                pumpkin_inventory::player::player_inventory::PlayerInventory::OFF_HAND_SLOT
            };
            player.sync_hand_slot(slot, ItemStack::EMPTY.clone());
        }

        player.living_entity.clear_active_hand();
    }

    fn can_mine(&self, player: &Player) -> bool {
        player.gamemode.load() != GameMode::Creative
    }

    fn get_use_duration(&self) -> i32 {
        Self::USE_DURATION
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

impl TridentItem {
    const USE_DURATION: i32 = 72000;
    const THROW_THRESHOLD_TIME: i32 = 10;
    const BASE_DAMAGE: f32 = 8.0;
    const SPIN_ATTACK_TICKS: i32 = 20;
    const GROUND_LIFT: f64 = 1.1999999;

    const fn equipment_slot(hand: Hand) -> EquipmentSlot {
        if matches!(hand, Hand::Right) {
            EquipmentSlot::MAIN_HAND
        } else {
            EquipmentSlot::OFF_HAND
        }
    }

    fn riptide_impulse(yaw: f32, pitch: f32, strength: f32) -> Vector3<f64> {
        let direction = Vector3::rotation_vector(pitch, yaw);
        let scale = strength
            / (direction.x * direction.x + direction.y * direction.y + direction.z * direction.z)
                .sqrt();
        Vector3::new(
            f64::from(direction.x * scale),
            f64::from(direction.y * scale),
            f64::from(direction.z * scale),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::{EnchantmentHelper, Item, ItemStack, TridentItem};
    use pumpkin_data::Enchantment;
    use pumpkin_data::sound::Sound;

    #[test]
    fn riptide_uses_enchantment_strength_and_clamps_sound_level() {
        for (level, expected_strength, expected_sound) in [
            (1, 1.5, Sound::ItemTridentRiptide1),
            (2, 2.25, Sound::ItemTridentRiptide2),
            (3, 3.0, Sound::ItemTridentRiptide3),
            (5, 4.5, Sound::ItemTridentRiptide3),
        ] {
            let mut stack = ItemStack::new(1, &Item::TRIDENT);
            stack.enchant(&Enchantment::RIPTIDE, level);
            let strength = EnchantmentHelper::modify_trident_spin_attack_strength(&stack, 0.0);
            let impulse = TridentItem::riptide_impulse(0.0, 0.0, strength);
            assert!((impulse.z - expected_strength).abs() < 1.0e-6);
            assert!(impulse.x.abs() < 1.0e-6);
            assert!(impulse.y.abs() < 1.0e-6);
            let west = TridentItem::riptide_impulse(90.0, 0.0, strength);
            assert!((west.x + expected_strength).abs() < 1.0e-6);
            assert!(west.y.abs() < 1.0e-6 && west.z.abs() < 1.0e-6);
            let up = TridentItem::riptide_impulse(0.0, -90.0, strength);
            assert!((up.y - expected_strength).abs() < 1.0e-6);
            assert!(up.x.abs() < 1.0e-6 && up.z.abs() < 1.0e-6);
            assert_eq!(
                EnchantmentHelper::pick_trident_sound(&stack),
                Some(expected_sound)
            );
        }
    }
}
