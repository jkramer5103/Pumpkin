use super::EnderDragonPhase;
use crate::entity::EntityBase;
use crate::entity::player::Player;
use crate::entity::{
    Entity,
    boss::ender_dragon::{DragonNode, EnderDragonEntity, NODE_COUNT, Vector3Ext, find_path},
    projectile::dragon_fireball::DragonFireballEntity,
};
use pumpkin_data::entity::EntityType;
use pumpkin_util::math::vector3::Vector3;
use std::collections::VecDeque;
use std::sync::{
    Mutex,
    atomic::{AtomicBool, Ordering},
};

#[derive(Default)]
pub struct StrafingPhase {
    holding_pattern_clockwise: AtomicBool,
    current_path: Mutex<Option<VecDeque<DragonNode>>>,
}

impl StrafingPhase {
    pub fn set_target(&self, dragon: &EnderDragonEntity, target: &Player) {
        *dragon
            .target_player
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = Some(target.gameprofile.id);
        let pos = dragon.mob_entity.living_entity.entity.pos.load();
        let target_pos = target.get_entity().pos.load();
        let current_node = dragon.find_closest_node();
        let target_node = dragon.find_closest_node_to(target_pos);
        let x = target_pos.x.floor();
        let z = target_pos.z.floor();
        let distance = (x - pos.x).hypot(z - pos.z);
        let height_offset = (f64::from(0.4f32) + distance / 80.0 - 1.0).min(10.0);
        let final_node = DragonNode::new(x, (target_pos.y + height_offset).floor(), z);
        let nodes = dragon
            .nodes
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let route = Self::path_to_target(
            &nodes,
            current_node,
            target_node,
            final_node,
            dragon.has_alive_crystals(),
        );
        drop(nodes);
        let mut path = self
            .current_path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        *path = route;
        Self::navigate_to_next_path_node(dragon, &mut path);
    }

    fn path_to_target(
        nodes: &[Option<DragonNode>; NODE_COUNT],
        from: usize,
        to: usize,
        final_node: DragonNode,
        crystals_alive: bool,
    ) -> Option<VecDeque<DragonNode>> {
        let route = find_path(nodes, from, to, crystals_alive)?;
        let mut path: VecDeque<_> = route.into_iter().filter_map(|index| nodes[index]).collect();
        // find_path already skips the starting node. The player waypoint is off-graph.
        path.push_back(final_node);
        Some(path)
    }

    fn navigate_to_next_path_node(
        dragon: &EnderDragonEntity,
        path: &mut Option<VecDeque<DragonNode>>,
    ) {
        if let Some(node) = path.as_mut().and_then(VecDeque::pop_front) {
            let y = f64::from(node.y as f32 + rand::random::<f32>() * 20.0);
            *dragon
                .target_location
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) =
                Some(Vector3::new(node.x, y, node.z));
        }
    }

    const fn next_orbit_node(current_node: usize, clockwise: bool, crystals_alive: bool) -> usize {
        let target_node = current_node as i32 + if clockwise { 1 } else { -1 };
        if crystals_alive {
            target_node.rem_euclid(12) as usize
        } else {
            (target_node - 12).rem_euclid(8) as usize + 12
        }
    }
}

impl super::Phase for StrafingPhase {
    fn get_type(&self) -> EnderDragonPhase {
        EnderDragonPhase::Strafing
    }

    fn begin(&self, dragon: &EnderDragonEntity) {
        *dragon
            .fireball_charge
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
        *dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
        *dragon
            .target_player
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
        *self
            .current_path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
    }

    #[expect(clippy::too_many_lines)]
    fn tick(&self, dragon: &EnderDragonEntity) {
        let target_id = *dragon
            .target_player
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let world = dragon.mob_entity.living_entity.entity.world.load();
        let pos = dragon.mob_entity.living_entity.entity.pos.load();

        let player_target = if let Some(id) = target_id {
            world
                .players
                .load()
                .iter()
                .find(|p| p.gameprofile.id == id)
                .cloned()
        } else {
            None
        };

        let Some(player) = player_target else {
            dragon.set_phase(EnderDragonPhase::Circling);
            return;
        };

        let player_pos = player.get_entity().pos.load();
        let mut path = self
            .current_path
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let mut target_location = dragon
            .target_location
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);

        if path.as_ref().is_some_and(VecDeque::is_empty) {
            let d2 = player_pos.x - pos.x;
            let d3 = player_pos.z - pos.z;
            let d4 = d2.hypot(d3);
            let d5 = (f64::from(0.4f32) + d4 / 80.0 - 1.0).min(10.0);
            *target_location = Some(Vector3::new(player_pos.x, player_pos.y + d5, player_pos.z));
        }

        let d11 = target_location
            .map(|loc| pos.distance_squared(loc))
            .unwrap_or(0.0);
        drop(target_location);
        if !(100.0..=22500.0).contains(&d11)
            || dragon
                .mob_entity
                .living_entity
                .entity
                .horizontal_collision
                .load(Ordering::Relaxed)
        {
            if path.as_ref().is_none_or(VecDeque::is_empty) {
                let i = dragon.find_closest_node();
                let mut j = i;
                if rand::random_range(0..8) == 0 {
                    self.holding_pattern_clockwise
                        .fetch_xor(true, Ordering::Relaxed);
                    j += 6;
                }
                let crystals_alive = dragon.has_alive_crystals();
                let j = Self::next_orbit_node(
                    j,
                    self.holding_pattern_clockwise.load(Ordering::Relaxed),
                    crystals_alive,
                );
                let nodes = dragon
                    .nodes
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                *path = find_path(&nodes, i, j, crystals_alive)
                    .map(|route| route.into_iter().filter_map(|index| nodes[index]).collect());
            }
            Self::navigate_to_next_path_node(dragon, &mut path);
        }
        drop(path);

        if player_pos.distance_squared(pos) < 4096.0
            && dragon
                .mob_entity
                .living_entity
                .entity
                .has_line_of_sight(player.get_entity())
        {
            let mut charge = dragon
                .fireball_charge
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);

            let aim_diff = Vector3::new(player_pos.x - pos.x, 0.0, player_pos.z - pos.z);
            let aim = if aim_diff.length_squared() > 1e-6 {
                aim_diff.normalize()
            } else {
                Vector3::new(0.0, 0.0, 0.0)
            };

            let yaw = dragon.mob_entity.living_entity.entity.yaw.load();
            let dir = Vector3::new(
                (yaw * (std::f32::consts::PI / 180.0)).sin() as f64,
                0.0,
                -(yaw * (std::f32::consts::PI / 180.0)).cos() as f64,
            );

            let dir_norm = if dir.length_squared() > 1e-6 {
                dir.normalize()
            } else {
                Vector3::new(0.0, 0.0, 0.0)
            };

            let dot = dir_norm.dot(&aim) as f32;
            let angle_degs = dot.acos().to_degrees() + 0.5;

            *charge += 1;

            if *charge >= 5 && angle_degs < 10.0 {
                *charge = 0;
                drop(charge);

                let entity = &dragon.mob_entity.living_entity.entity;
                let head = &dragon.parts[0].entity;
                let head_pos = head.pos.load();
                let yaw = -entity.yaw.load() * (std::f32::consts::PI / 180.0);
                let pitch = entity.pitch.load() * (std::f32::consts::PI / 180.0);
                let view = Vector3::new(
                    f64::from(pumpkin_util::math::sin(yaw) * pumpkin_util::math::cos(pitch)),
                    f64::from(-pumpkin_util::math::sin(pitch)),
                    f64::from(pumpkin_util::math::cos(yaw) * pumpkin_util::math::cos(pitch)),
                );
                let start = Vector3::new(
                    head_pos.x - view.x,
                    head_pos.y + f64::from(head.entity_dimension.load().height) * 0.5 + 0.5,
                    head_pos.z - view.z,
                );
                let target = player_pos.add_raw(
                    0.0,
                    f64::from(player.get_entity().entity_dimension.load().height) * 0.5,
                    0.0,
                );
                if !entity.is_silent() {
                    world.sync_world_event(
                        pumpkin_data::world::WorldEvent::SoundDragonFireball,
                        entity.block_pos.load(),
                        0,
                    );
                }
                let fireball = DragonFireballEntity::new_shot(
                    Entity::new(world.clone(), start, &EntityType::DRAGON_FIREBALL),
                    entity,
                    target - start,
                );
                world.spawn_entity(std::sync::Arc::new(fireball));

                if let Some(path) = self
                    .current_path
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner)
                    .as_mut()
                {
                    path.clear();
                }
                dragon.set_phase(EnderDragonPhase::Circling);
            }
        } else {
            let mut charge = dragon
                .fireball_charge
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if *charge > 0 {
                *charge -= 1;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::StrafingPhase;
    use crate::entity::boss::ender_dragon::{DragonNode, NODE_COUNT, find_path};

    #[test]
    fn strafe_approach_keeps_graph_hops_before_the_off_graph_player_node() {
        let mut nodes = [None; NODE_COUNT];
        nodes[20] = Some(DragonNode::new(20.0, 73.0, 0.0));
        nodes[19] = Some(DragonNode::new(28.0, 73.0, -29.0));
        nodes[12] = Some(DragonNode::new(40.0, 73.0, 0.0));
        nodes[0] = Some(DragonNode::new(60.0, 73.0, 0.0));
        let player = DragonNode::new(8.0, 139.0, 0.0);
        for (from, to, expected) in [
            (20, 19, Some(vec![(28.0, 73.0, -29.0), (8.0, 139.0, 0.0)])),
            (20, 20, Some(vec![(8.0, 139.0, 0.0)])),
            (12, 0, None),
        ] {
            let path = StrafingPhase::path_to_target(&nodes, from, to, player, false);
            let coordinates = path.map(|path| {
                path.into_iter()
                    .map(|node| (node.x, node.y, node.z))
                    .collect::<Vec<_>>()
            });
            assert_eq!(coordinates, expected);
        }
    }

    #[test]
    fn strafe_orbits_leave_the_player_node_and_wrap_the_active_ring() {
        for (current, clockwise, crystals, target) in [
            (20, false, false, 19),
            (20, true, false, 13),
            (12, false, false, 19),
            (19, true, false, 12),
            (0, false, true, 11),
            (11, true, true, 0),
            (20, false, true, 7),
            (26, true, false, 19),
        ] {
            assert_eq!(
                StrafingPhase::next_orbit_node(current, clockwise, crystals),
                target,
            );
        }

        // In the arena both dragon and player are nearest node 20. Retargeting
        // the player returns no hops; vanilla instead flies toward node 19.
        let mut nodes = [None; NODE_COUNT];
        nodes[20] = Some(DragonNode::new(20.0, 73.0, 0.0));
        nodes[19] = Some(DragonNode::new(28.0, 73.0, -29.0));
        assert_eq!(find_path(&nodes, 20, 20, false), Some(vec![]));
        let target = StrafingPhase::next_orbit_node(20, false, false);
        assert_eq!(find_path(&nodes, 20, target, false), Some(vec![19]));
    }
}
