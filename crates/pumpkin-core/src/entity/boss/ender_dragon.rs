use pumpkin_data::damage::DamageType;
use pumpkin_data::entity::EntityType;
use pumpkin_data::game_event::GameEvent;
use pumpkin_data::tag::{self, Taggable};
use pumpkin_data::{Block, BlockStateId};
use pumpkin_nbt::compound::NbtCompound;
use pumpkin_util::gamemode::GameMode;
use pumpkin_util::math::boundingbox::{BoundingBox, EntityDimensions};
use pumpkin_util::math::position::BlockPos;
use pumpkin_util::math::vector3::Vector3;
use pumpkin_util::math::{cos, sin, wrap_degrees};
use pumpkin_world::{chunk::ChunkHeightmapType, world::BlockFlags};
use std::sync::atomic::Ordering;
use std::sync::{Arc, Mutex};

use crate::entity::{
    Entity, EntityBase,
    living::LivingEntity,
    mob::{Mob, MobEntity},
    player::Player,
};

pub mod flight_history;
pub mod phase;

use flight_history::DragonFlightHistory;
use phase::{EnderDragonPhase, PhaseManager};

pub const NODE_COUNT: usize = 24;
pub const NODE_Y: i32 = 105;
pub const NODE_REACH_SQ: f64 = 64.0;
pub const DEATH_TIMER_MAX: i32 = 200;
const GROWL_COOLDOWN_BASE: i32 = 200;
const FLAP_SPEED: f32 = 0.2;
pub const FLY_ACCEL: f64 = 0.1;
pub const FLY_SPEED: f64 = 0.6;
const ARENA_RADIUS: f64 = 192.0;
const PART_DIMENSIONS: [(f32, f32); 8] = [
    (1.0, 1.0), // Head
    (3.0, 3.0), // Neck
    (5.0, 3.0), // Body
    (2.0, 2.0), // Tails
    (2.0, 2.0),
    (2.0, 2.0),
    (4.0, 2.0), // Wings
    (4.0, 2.0),
];

const NODE_ADJACENCY: [u32; NODE_COUNT] = [
    6146, 8197, 8202, 16404, 32808, 32848, 65696, 131392, 131712, 263424, 526848, 525313, 1581057,
    3166214, 2138120, 6373424, 4358208, 12910976, 9044480, 9706496, 15216640, 13688832, 11763712,
    8257536,
];

#[derive(Clone, Copy, Default, Debug)]
pub struct DragonNode {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl DragonNode {
    #[must_use]
    pub const fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }

    #[inline]
    #[must_use]
    pub fn dist_sq(&self, other: &Self) -> f64 {
        let (dx, dy, dz) = (self.x - other.x, self.y - other.y, self.z - other.z);
        dx * dx + dy * dy + dz * dz
    }

    #[inline]
    #[must_use]
    pub fn dist_sq_vec(&self, v: Vector3<f64>) -> f64 {
        let (dx, dy, dz) = (self.x - v.x, self.y - v.y, self.z - v.z);
        dx * dx + dy * dy + dz * dz
    }

    #[inline]
    #[must_use]
    pub const fn as_vec3(&self) -> Vector3<f64> {
        Vector3::new(self.x, self.y, self.z)
    }
}

#[must_use]
pub fn find_path(
    nodes: &[Option<DragonNode>; NODE_COUNT],
    from: usize,
    to: usize,
    final_node: Option<DragonNode>,
    crystals_alive: bool,
) -> Vec<usize> {
    if from == to && final_node.is_none() {
        return vec![];
    }

    let mut g = [f64::MAX; NODE_COUNT];
    let mut came_from = [NODE_COUNT; NODE_COUNT];
    let mut closed = [false; NODE_COUNT];
    let mut open: std::collections::BinaryHeap<(ordered_float::OrderedFloat<f64>, usize)> =
        std::collections::BinaryHeap::new();

    let h = |n: usize| -> f64 {
        if let Some(target) = final_node
            && let Some(node) = nodes[n]
        {
            return node.dist_sq(&target).sqrt();
        }
        match (nodes[n], nodes[to]) {
            (Some(a), Some(b)) => a.dist_sq(&b).sqrt(),
            _ => 0.0,
        }
    };

    g[from] = 0.0;
    open.push((ordered_float::OrderedFloat(-h(from)), from));

    let start_index = if crystals_alive { 0 } else { 12 };
    'outer: while let Some((_, cur)) = open.pop() {
        if closed[cur] {
            continue;
        }
        if cur == to {
            break 'outer;
        }
        closed[cur] = true;

        let adj = NODE_ADJACENCY[cur];
        for nbr in start_index..NODE_COUNT {
            if (adj >> nbr) & 1 == 0 || closed[nbr] {
                continue;
            }
            let (Some(cn), Some(nn)) = (nodes[cur], nodes[nbr]) else {
                continue;
            };
            let ng = g[cur] + cn.dist_sq(&nn).sqrt();
            if ng < g[nbr] {
                g[nbr] = ng;
                came_from[nbr] = cur;
                open.push((ordered_float::OrderedFloat(-(ng + h(nbr))), nbr));
            }
        }
    }

    let mut path = Vec::new();
    let mut cur = to;
    while cur != NODE_COUNT {
        path.push(cur);
        cur = came_from[cur];
    }
    path.reverse();
    if path.first() == Some(&from) {
        path.remove(0);
    }
    path
}

pub struct EnderDragonPart {
    pub entity: Entity,
    pub dragon_uuid: uuid::Uuid,
}

impl EnderDragonPart {
    pub const fn new(entity: Entity, dragon_uuid: uuid::Uuid) -> Self {
        Self {
            entity,
            dragon_uuid,
        }
    }
}

impl EntityBase for EnderDragonPart {
    fn get_entity(&self) -> &Entity {
        &self.entity
    }

    fn damage(&self, source: &dyn EntityBase, amount: f32, damage_type: DamageType) -> bool {
        let world = self.entity.world.load();
        if let Some(dragon_base) = world
            .entities
            .load()
            .iter()
            .find(|e| e.get_entity().entity_uuid == self.dragon_uuid)
        {
            return dragon_base.damage(source, amount, damage_type);
        }
        false
    }

    fn cast_any(&self) -> &dyn std::any::Any {
        self
    }

    fn get_living_entity(&self) -> Option<&LivingEntity> {
        None
    }
    fn can_hit(&self) -> bool {
        true
    }
}

pub struct EnderDragonEntity {
    pub mob_entity: MobEntity,
    pub parts: Vec<Arc<EnderDragonPart>>,

    pub flight_history: Mutex<DragonFlightHistory>,
    pub flap_time: Mutex<f32>,
    pub o_flap_time: Mutex<f32>,

    pub in_wall: Mutex<bool>,
    pub dragon_death_time: Mutex<i32>,
    pub sitting_damage_received: Mutex<f32>,

    pub nodes_initialized: Mutex<bool>,

    pub fight_origin: Mutex<BlockPos>,

    pub phase_manager: PhaseManager,
    pub phase: Mutex<EnderDragonPhase>,
    pub growl_time: Mutex<i32>,
    pub yaw_rot_accel: Mutex<f32>,
    pub holding_pattern_clockwise: Mutex<bool>,
    pub target_location: Mutex<Option<Vector3<f64>>>,
    pub fireball_charge: Mutex<i32>,
    pub time_since_charge: Mutex<i32>,

    pub nodes: Mutex<[Option<DragonNode>; NODE_COUNT]>,
    pub path: Mutex<Vec<usize>>,

    pub strafe_target: Mutex<Option<Vector3<f64>>>,
    pub target_player: Mutex<Option<uuid::Uuid>>,
    pub ticks_sitting: Mutex<i32>,
    pub scanning_time: Mutex<i32>,
    pub sit_attack_timer: Mutex<i32>,
    pub breathing_timer: Mutex<i32>,
    pub flame_count: Mutex<i32>,
    pub flame: Mutex<Option<uuid::Uuid>>,
}

impl EnderDragonEntity {
    pub fn new(entity: Entity) -> Arc<Self> {
        entity.no_physics.store(true, Ordering::Relaxed);
        let base_id = entity.entity_id;
        let dragon_uuid = entity.entity_uuid;
        let world = entity.world.load();

        let _ = Entity::reserve_ids(8);

        let mut parts = Vec::new();
        for (i, (width, height)) in PART_DIMENSIONS.iter().enumerate() {
            let part_entity = Entity::from_uuid_with_id(
                base_id + i as i32 + 1,
                uuid::Uuid::new_v4(),
                world.clone(),
                entity.pos.load(),
                &EntityType::ENDER_DRAGON,
            );
            let dimensions = EntityDimensions::new(*width, *height, *height);
            part_entity.entity_dimension.store(dimensions);
            let part_pos = part_entity.pos.load();
            part_entity.bounding_box.store(BoundingBox::new_from_pos(
                part_pos.x,
                part_pos.y,
                part_pos.z,
                &dimensions,
            ));
            let part = Arc::new(EnderDragonPart::new(part_entity, dragon_uuid));
            // TODO: world.add_entity_silent(part.clone() as Arc<dyn EntityBase>);
            parts.push(part);
        }

        Arc::new(Self {
            mob_entity: MobEntity::new(entity),
            parts,
            flight_history: Mutex::new(DragonFlightHistory::default()),
            flap_time: Mutex::new(0.0),
            o_flap_time: Mutex::new(0.0),
            in_wall: Mutex::new(false),
            dragon_death_time: Mutex::new(0),
            sitting_damage_received: Mutex::new(0.0),
            nodes_initialized: Mutex::new(false),
            fight_origin: Mutex::new(BlockPos::new(0, 128, 0)),
            phase_manager: PhaseManager::new(),
            phase: Mutex::new(EnderDragonPhase::Hovering),
            growl_time: Mutex::new(GROWL_COOLDOWN_BASE),
            yaw_rot_accel: Mutex::new(0.0),
            holding_pattern_clockwise: Mutex::new(false),
            target_location: Mutex::new(None),
            fireball_charge: Mutex::new(0),
            time_since_charge: Mutex::new(0),
            nodes: Mutex::new([None; NODE_COUNT]),
            path: Mutex::new(Vec::new()),
            strafe_target: Mutex::new(None),
            target_player: Mutex::new(None),
            ticks_sitting: Mutex::new(0),
            scanning_time: Mutex::new(0),
            sit_attack_timer: Mutex::new(0),
            breathing_timer: Mutex::new(0),
            flame_count: Mutex::new(0),
            flame: Mutex::new(None),
        })
    }

    pub fn set_fight_origin(&self, pos: BlockPos) {
        if let (Ok(mut initialized), Ok(mut origin)) = (
            self.nodes_initialized.try_lock(),
            self.fight_origin.try_lock(),
        ) && *origin != pos
        {
            *origin = pos;
            *initialized = false;
        }
    }

    pub fn set_phase(&self, phase_type: EnderDragonPhase) {
        let mut phase_lock = self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if *phase_lock == phase_type {
            return;
        }

        let old_phase = self.phase_manager.get_phase(*phase_lock);
        old_phase.end(self);

        *phase_lock = phase_type;

        let new_phase = self.phase_manager.get_phase(phase_type);
        new_phase.begin(self);
    }

    fn flight_node_horizontal_position(index: usize) -> (i32, i32) {
        let (radius, count, multiplier) = if index < 12 {
            (60.0, 12, index)
        } else if index < 20 {
            (40.0, 8, index - 12)
        } else {
            (20.0, 4, index - 20)
        };
        // Keep vanilla's shifted float angle: lookup-table rounding changes block columns.
        let angle = 2.0
            * (-std::f32::consts::PI
                + (std::f64::consts::PI / f64::from(count)) as f32 * multiplier as f32);
        (
            (radius * cos(angle)).floor() as i32,
            (radius * sin(angle)).floor() as i32,
        )
    }

    fn ensure_nodes_initialized(&self) {
        let mut initialized = self
            .nodes_initialized
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if *initialized {
            return;
        }

        let world = self.mob_entity.living_entity.entity.world.load();
        let fight_origin = self
            .fight_origin
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);

        let mut nodes = self
            .nodes
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        for i in 0..NODE_COUNT {
            let (offset_x, offset_z) = Self::flight_node_horizontal_position(i);
            let node_x = fight_origin.0.x + offset_x;
            let node_z = fight_origin.0.z + offset_z;
            let y_adjustment = if (12..20).contains(&i) { 15 } else { 5 };

            // Pumpkin's heightmap returns the top block, not the space above it.
            let height = world.get_heightmap_height(
                ChunkHeightmapType::MotionBlockingNoLeaves,
                node_x,
                node_z,
            ) + 1;
            let node_y = 73.max(height + y_adjustment);
            nodes[i] = Some(DragonNode::new(node_x as f64, node_y as f64, node_z as f64));
        }

        *initialized = true;
    }

    pub fn find_closest_node(&self) -> usize {
        let pos = self.mob_entity.living_entity.entity.pos.load();
        self.find_closest_node_to(pos)
    }

    pub fn find_closest_node_to(&self, pos: Vector3<f64>) -> usize {
        self.ensure_nodes_initialized();
        let nodes = self
            .nodes
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        Self::nearest_node_in(&nodes, pos, self.has_alive_crystals())
    }

    fn has_alive_crystals(&self) -> bool {
        let world = self.mob_entity.living_entity.entity.world.load();
        world.dragon_fight.as_ref().is_some_and(|fight| {
            fight
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .alive_crystals()
                > 0
        })
    }

    fn nearest_node_in(
        nodes: &[Option<DragonNode>; NODE_COUNT],
        pos: Vector3<f64>,
        crystals_alive: bool,
    ) -> usize {
        // Vanilla compares pathfinder Nodes, whose coordinates are floored integers.
        let pos = Vector3::new(pos.x.floor(), pos.y.floor(), pos.z.floor());
        let start_index = if crystals_alive { 0 } else { 12 };
        let mut closest_dist = 10000.0f32;
        let mut closest_index = 0;
        for (index, node) in nodes.iter().enumerate().skip(start_index) {
            if let Some(node) = node {
                let dist = node.dist_sq_vec(pos) as f32;
                if dist < closest_dist {
                    closest_dist = dist;
                    closest_index = index;
                }
            }
        }
        closest_index
    }

    #[inline]
    #[must_use]
    pub fn yaw_toward(from: Vector3<f64>, to: Vector3<f64>) -> f32 {
        (-(to.z - from.z)).atan2(to.x - from.x).to_degrees() as f32 - 90.0
    }

    pub fn move_relative(&self, speed: f32, relative_movement: Vector3<f64>) {
        let yaw = self.mob_entity.living_entity.entity.yaw.load();
        let movement = Self::get_relative_movement(relative_movement, speed, yaw);
        let entity = &self.mob_entity.living_entity.entity;
        let vel = entity.velocity.load();
        entity.velocity.store(vel + movement);
    }

    fn get_relative_movement(
        relative_movement: Vector3<f64>,
        speed: f32,
        yaw: f32,
    ) -> Vector3<f64> {
        let dist = relative_movement.length_squared();
        if dist < 1.0E-7 {
            return Vector3::new(0.0, 0.0, 0.0);
        }
        let vec = if dist > 1.0 {
            relative_movement.normalize()
        } else {
            relative_movement
        } * (speed as f64);
        let sin = (yaw * (std::f32::consts::PI / 180.0)).sin() as f64;
        let cos = (yaw * (std::f32::consts::PI / 180.0)).cos() as f64;
        Vector3::new(vec.x * cos - vec.z * sin, vec.y, vec.z * cos + vec.x * sin)
    }

    fn flight_turn_delta(xdd: f64, zdd: f64, yaw: f32) -> f32 {
        // Vanilla wraps to [-180, 180), so an exact reversal turns negatively.
        wrap_degrees(180.0 - (xdd.atan2(zdd).to_degrees() as f32) - yaw).clamp(-50.0, 50.0)
    }

    pub fn steer_toward(
        &self,
        pos: Vector3<f64>,
        target: Vector3<f64>,
        fly_speed: f32,
        turn_speed: f32,
    ) {
        let xdd = target.x - pos.x;
        let mut ydd = target.y - pos.y;
        let zdd = target.z - pos.z;
        let dist_sq = xdd * xdd + ydd * ydd + zdd * zdd;

        let horizontal_dist = xdd.hypot(zdd);
        if horizontal_dist > 0.0 {
            ydd = (ydd / horizontal_dist).clamp(-(fly_speed as f64), fly_speed as f64);
        }

        let entity = &self.mob_entity.living_entity.entity;
        let mut vel = entity.velocity.load();
        vel.y += ydd * 0.01;
        entity.velocity.store(vel);

        let yaw = entity.yaw.load();
        let aim_diff = target - pos;
        let aim = if aim_diff.length_squared() > 1e-6 {
            aim_diff.normalize()
        } else {
            Vector3::new(0.0, 0.0, 0.0)
        };

        let dir_vec = Vector3::new(
            (yaw * (std::f32::consts::PI / 180.0)).sin() as f64,
            vel.y,
            -(yaw * (std::f32::consts::PI / 180.0)).cos() as f64,
        );
        let dir = if dir_vec.length_squared() > 1e-6 {
            dir_vec.normalize()
        } else {
            Vector3::new(0.0, 0.0, 0.0)
        };

        let dot = (dir.dot(&aim) as f32 + 0.5).max(0.0) / 1.5;
        if xdd.abs() > 1.0E-5 || zdd.abs() > 1.0E-5 {
            let y_rot_d = Self::flight_turn_delta(xdd, zdd, yaw);

            let mut y_rot_a = self
                .yaw_rot_accel
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            *y_rot_a *= 0.8;
            *y_rot_a += y_rot_d * turn_speed;
            entity.yaw.store(yaw + *y_rot_a * 0.1);
        }

        let span = (2.0 / (dist_sq + 1.0)) as f32;
        self.move_relative(
            0.06 * (dot * span + (1.0 - span)),
            Vector3::new(0.0, 0.0, -1.0),
        );

        // Dragon flight moves with the accelerated velocity, before applying drag.
        let in_wall = *self
            .in_wall
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let movement = if in_wall {
            entity.velocity.load() * f64::from(0.8f32)
        } else {
            entity.velocity.load()
        };
        entity.move_entity(self, movement);

        let actual_vel = entity.velocity.load();
        let actual_dir = if actual_vel.length_squared() > 1e-6 {
            actual_vel.normalize()
        } else {
            Vector3::new(0.0, 0.0, 0.0)
        };
        let slide = 0.8 + 0.15 * (actual_dir.dot(&dir) + 1.0) / 2.0;
        entity.velocity.store(Vector3::new(
            actual_vel.x * slide,
            actual_vel.y * f64::from(0.91f32),
            actual_vel.z * slide,
        ));
    }

    fn update_flap_time(&self) {
        let sitting = self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .is_sitting();
        let in_wall = *self
            .in_wall
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let mut flap = self
            .flap_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let mut o_flap = self
            .o_flap_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);

        *o_flap = *flap;
        *flap += if sitting {
            0.1
        } else if in_wall {
            FLAP_SPEED * 0.5
        } else {
            FLAP_SPEED
        };
        if *flap > std::f32::consts::TAU {
            *flap -= std::f32::consts::TAU;
        }
    }

    fn tick_growl(&self) {
        if self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .is_sitting()
        {
            return;
        }
        let mut t = self
            .growl_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if *t > 0 {
            *t -= 1;
        } else {
            *t = GROWL_COOLDOWN_BASE + rand::random_range(0..100);
        }
    }

    fn find_nearest_player(&self) -> Option<Arc<Player>> {
        let world = self.mob_entity.living_entity.entity.world.load();
        let pos = self.mob_entity.living_entity.entity.pos.load();
        world
            .players
            .load()
            .iter()
            .filter(|p| {
                let p_pos = p.living_entity.entity.pos.load();
                p_pos.distance_squared(pos) < ARENA_RADIUS * ARENA_RADIUS
            })
            .min_by(|a, b| {
                let a_pos = a.living_entity.entity.pos.load();
                let b_pos = b.living_entity.entity.pos.load();
                a_pos
                    .distance_squared(pos)
                    .total_cmp(&b_pos.distance_squared(pos))
            })
            .cloned()
    }

    fn body_position(&self) -> Vector3<f64> {
        let entity = &self.mob_entity.living_entity.entity;
        let pos = entity.pos.load();
        let rot = entity.yaw.load() * (std::f32::consts::PI / 180.0);
        Vector3::new(
            pos.x + f64::from(rot.sin()) * 0.5,
            pos.y,
            pos.z - f64::from(rot.cos()) * 0.5,
        )
    }

    fn knockback_push(body_pos: Vector3<f64>, target_pos: Vector3<f64>) -> Vector3<f64> {
        let xd = target_pos.x - body_pos.x;
        let zd = target_pos.z - body_pos.z;
        let dd = (xd * xd + zd * zd).max(0.1);
        Vector3::new(xd / dd * 4.0, f64::from(0.2f32), zd / dd * 4.0)
    }

    const fn can_collide_with_player(gamemode: GameMode, hurt_time: i32) -> bool {
        // Mob AI runs before LivingEntity::tick here; vanilla counts down before AI.
        hurt_time <= 1 && !matches!(gamemode, GameMode::Creative | GameMode::Spectator)
    }

    const fn can_damage_contact_victim(ticks_since_last_hurt_by_mob: i32) -> bool {
        ticks_since_last_hurt_by_mob > 2
    }

    fn handle_player_collisions(&self) {
        let hurt_time = self
            .mob_entity
            .living_entity
            .hurt_time
            .load(Ordering::Relaxed);
        let world = self.mob_entity.living_entity.entity.world.load();

        let dragon_bbox = self.mob_entity.living_entity.entity.bounding_box.load();
        let body_pos = self.body_position();

        for player in world
            .players
            .load()
            .iter()
            .filter(|player| Self::can_collide_with_player(player.gamemode.load(), hurt_time))
        {
            if player
                .living_entity
                .entity
                .bounding_box
                .load()
                .intersects(&dragon_bbox)
            {
                let player_pos = player.get_entity().pos.load();
                player
                    .get_entity()
                    .add_velocity(Self::knockback_push(body_pos, player_pos));

                if !self
                    .phase
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner)
                    .is_sitting()
                    && Self::can_damage_contact_victim(
                        player.living_entity.ticks_since_last_hurt_by_mob(),
                    )
                {
                    player.damage(self, 5.0, DamageType::MOB_ATTACK);
                }
            }
        }
    }

    fn tick_crystal_healing(&self) {
        let world = self.mob_entity.living_entity.entity.world.load();
        let pos = self.mob_entity.living_entity.entity.pos.load();

        let mut nearest_crystal = None;
        let mut min_dist_sq = 1024.0; // 32 blocks

        for entity in world.entities.load().iter() {
            if entity.get_entity().entity_type == &EntityType::END_CRYSTAL {
                let crystal_pos = entity.get_entity().pos.load();
                let dist_sq = pos.distance_squared(crystal_pos);
                if dist_sq < min_dist_sq {
                    min_dist_sq = dist_sq;
                    nearest_crystal = Some(entity.clone());
                }
            }
        }

        if let Some(_crystal) = nearest_crystal {
            let living = &self.mob_entity.living_entity;
            if living.health.load() < living.get_max_health() {
                living.heal(1.0);
            }
        }
    }

    fn can_destroy_block(block: &Block, mob_griefing: bool) -> bool {
        mob_griefing
            && !block.is_air()
            && !block.has_tag(&tag::Block::MINECRAFT_DRAGON_TRANSPARENT)
            && !block.has_tag(&tag::Block::MINECRAFT_DRAGON_IMMUNE)
    }

    fn check_walls(&self, bbox: BoundingBox) -> bool {
        let world = self.mob_entity.living_entity.entity.world.load();
        let min = bbox.min_block_pos();
        // Vanilla checkWalls includes blocks on the maximum faces, too.
        let max = BlockPos::floored_v(bbox.max);

        let mut hit_wall = false;
        let mob_griefing = world.level_info.load().game_rules.mob_griefing;
        for pos in BlockPos::iterate(min, max) {
            let block = world.get_block(&pos);
            if !block.is_air() && !block.has_tag(&tag::Block::MINECRAFT_DRAGON_TRANSPARENT) {
                if Self::can_destroy_block(block, mob_griefing) {
                    world.set_block_state(&pos, BlockStateId::AIR, BlockFlags::NOTIFY_ALL);
                } else {
                    hit_wall = true;
                }
            }
        }
        hit_wall
    }

    fn tick_parts(&self) {
        let history = self
            .flight_history
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let p5 = history.get(5);
        let p10 = history.get(10);
        let p0 = history.get(0);

        let tilt = (p5.y - p10.y) as f32 * 10.0 * (std::f32::consts::PI / 180.0);
        let cc_tilt = tilt.cos() as f64;
        let ss_tilt = tilt.sin() as f64;

        let yaw = self.mob_entity.living_entity.entity.yaw.load();
        let rot1 = yaw * (std::f32::consts::PI / 180.0);
        let ss1 = rot1.sin() as f64;
        let cc1 = rot1.cos() as f64;

        let pos = self.mob_entity.living_entity.entity.pos.load();

        // Body
        self.parts[2].entity.set_pos(self.body_position());

        // Wings
        self.parts[6].entity.set_pos(Vector3::new(
            pos.x + cc1 * 4.5,
            pos.y + 2.0,
            pos.z + ss1 * 4.5,
        ));
        self.parts[7].entity.set_pos(Vector3::new(
            pos.x - cc1 * 4.5,
            pos.y + 2.0,
            pos.z - ss1 * 4.5,
        ));

        let head_y_offset = if self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .is_sitting()
        {
            -1.0
        } else {
            p5.y - p0.y
        };

        let yaw_accel = *self
            .yaw_rot_accel
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let rot2 = yaw * (std::f32::consts::PI / 180.0) - yaw_accel * 0.01;
        let ss2 = rot2.sin() as f64;
        let cc2 = rot2.cos() as f64;

        // Head & Neck
        self.parts[0].entity.set_pos(Vector3::new(
            pos.x + ss2 * 6.5 * cc_tilt,
            pos.y + head_y_offset + ss_tilt * 6.5,
            pos.z - cc2 * 6.5 * cc_tilt,
        ));
        self.parts[1].entity.set_pos(Vector3::new(
            pos.x + ss2 * 5.5 * cc_tilt,
            pos.y + head_y_offset + ss_tilt * 5.5,
            pos.z - cc2 * 5.5 * cc_tilt,
        ));

        // Tails
        for i in 0..3 {
            let pi = history.get(12 + i * 2);
            let rot = yaw * (std::f32::consts::PI / 180.0)
                + (pi.y_rot - p5.y_rot).rem_euclid(360.0).to_radians();
            let ss = rot.sin() as f64;
            let cc = rot.cos() as f64;
            let dd = (i + 1) as f64 * 2.0;

            self.parts[3 + i as usize].entity.set_pos(Vector3::new(
                pos.x - (ss1 * 1.5 + ss * dd) * cc_tilt,
                pos.y + (pi.y - p5.y) - (dd + 1.5) * ss_tilt + 1.5,
                pos.z + (cc1 * 1.5 + cc * dd) * cc_tilt,
            ));
        }
    }

    fn update_fight(&self) {
        let world = self.mob_entity.living_entity.entity.world.load();
        if let Some(ref fight_mutex) = world.dragon_fight {
            let living = &self.mob_entity.living_entity;
            if let Ok(mut fight) = fight_mutex.lock() {
                let custom_name = living.entity.custom_name.load();
                fight.update_dragon(
                    &world,
                    living.entity.entity_uuid,
                    living.health.load(),
                    living.get_max_health(),
                    custom_name.as_ref().as_ref(),
                );
            }
        }
    }

    pub fn ai_step(&self) {
        if self.mob_entity.living_entity.entity.is_removed() {
            return;
        }
        self.mob_entity.living_entity.entity.update_last_pos();
        if self.mob_entity.living_entity.health.load() <= 0.0 {
            phase::DyingPhase::tick_death(self);
            return;
        }
        self.update_flap_time();
        self.tick_growl();
        self.tick_crystal_healing();

        // Vanilla checks crystals before NoAI, but skips flight and contact work.
        if self.mob_entity.is_no_ai() {
            *self
                .flap_time
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) = 0.5;
            return;
        }

        self.ensure_nodes_initialized();

        {
            let y = self.mob_entity.living_entity.entity.pos.load().y;
            let yaw = self.mob_entity.living_entity.entity.yaw.load();
            self.flight_history
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .record(y, yaw);
        };

        self.update_fight();

        let phase_type: EnderDragonPhase = *self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let mut phase = self.phase_manager.get_phase(phase_type);

        if phase_type.is_sitting() {
            *self
                .ticks_sitting
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) += 1;
        } else {
            self.handle_player_collisions();
        }

        phase.tick(self);

        if self.mob_entity.living_entity.entity.is_removed() {
            return;
        }

        let next_phase_type = *self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if next_phase_type != phase_type {
            // Vanilla ticks the newly selected phase once before steering.
            phase = self.phase_manager.get_phase(next_phase_type);
            phase.tick(self);
        }

        if self.mob_entity.living_entity.entity.is_removed() {
            return;
        }

        if phase.get_type() != EnderDragonPhase::Dying {
            let target_location = *self
                .target_location
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if let Some(target) = target_location {
                let pos = self.mob_entity.living_entity.entity.pos.load();
                self.steer_toward(
                    pos,
                    target,
                    phase.get_fly_speed(),
                    phase.get_turn_speed(self),
                );
            }
        }

        self.tick_parts();
        // Check every volume after movement; the next flight tick uses this result.
        let in_wall = self.check_walls(self.parts[0].entity.bounding_box.load())
            | self.check_walls(self.parts[1].entity.bounding_box.load())
            | self.check_walls(self.parts[2].entity.bounding_box.load());
        *self
            .in_wall
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = in_wall;
    }

    pub fn hurt(&self, damage: f32) {
        let phase_type: EnderDragonPhase = *self
            .phase
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if phase_type.is_sitting() {
            *self
                .sitting_damage_received
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) += damage;
        }
    }
}

impl Mob for EnderDragonEntity {
    fn get_mob_entity(&self) -> &MobEntity {
        &self.mob_entity
    }

    fn mob_write_nbt(&self, nbt: &mut NbtCompound) {
        nbt.put_int(
            "DragonPhase",
            self.phase
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .network_id(),
        );
        nbt.put_int(
            "DragonDeathTime",
            *self
                .dragon_death_time
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        );
    }

    fn mob_read_nbt(&self, nbt: &NbtCompound) {
        if let Some(phase) = nbt
            .get_int("DragonPhase")
            .and_then(EnderDragonPhase::from_network_id)
        {
            self.set_phase(phase);
        }
        *self
            .dragon_death_time
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) =
            nbt.get_int("DragonDeathTime").unwrap_or(0);
    }

    fn mob_tick(&self, _caller: &dyn EntityBase) {
        self.ai_step();
    }

    fn mob_kill(&self, _caller: &dyn EntityBase) {
        let entity = &self.mob_entity.living_entity.entity;
        let world = entity.world.load();
        entity.remove();
        for part in &self.parts {
            part.entity.remove();
        }
        world.emit_game_event(GameEvent::EntityDie.name(), entity.pos.load());
        self.update_fight();
        if let Some(ref fight_mutex) = world.dragon_fight {
            fight_mutex
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .set_dragon_killed(&world, entity.entity_uuid);
        }
    }

    fn on_damage(&self, _damage_type: DamageType, _source: Option<&dyn EntityBase>) {
        let living = &self.mob_entity.living_entity;
        if living.health.load() <= 0.0 {
            self.set_phase(EnderDragonPhase::Dying);
        }
    }

    fn get_mob_gravity(&self) -> f64 {
        0.0
    }
}

pub trait Vector3Ext {
    fn distance_squared(self, other: Self) -> f64;
}

impl Vector3Ext for Vector3<f64> {
    fn distance_squared(self, other: Self) -> f64 {
        let (dx, dy, dz) = (self.x - other.x, self.y - other.y, self.z - other.z);
        dx * dx + dy * dy + dz * dz
    }
}

#[cfg(test)]
mod tests {
    use super::{DragonNode, EnderDragonEntity, NODE_COUNT, find_path};
    use pumpkin_data::Block;
    use pumpkin_util::gamemode::GameMode;
    use pumpkin_util::math::vector3::Vector3;

    #[test]
    fn flight_paths_exclude_outer_detours_without_live_crystals() {
        // Raised middle-ring columns in the takeoff arena force an outer detour
        // only while crystals are alive. Vanilla climbs through node 13 otherwise.
        let mut nodes = [None; NODE_COUNT];
        for (index, x, y, z) in [
            (0, 60.0, 73.0, 0.0),
            (1, 51.0, 73.0, 30.0),
            (2, 29.0, 73.0, 51.0),
            (3, 0.0, 73.0, 60.0),
            (12, 40.0, 73.0, 0.0),
            (13, 28.0, 196.0, 28.0),
            (14, 0.0, 73.0, 40.0),
        ] {
            nodes[index] = Some(DragonNode::new(x, y, z));
        }
        assert_eq!(find_path(&nodes, 12, 14, None, false), [13, 14]);
        assert_eq!(find_path(&nodes, 14, 12, None, false), [13, 12]);
        assert_eq!(find_path(&nodes, 12, 14, None, true), [0, 1, 2, 3, 14]);
        assert_eq!(find_path(&nodes, 14, 12, None, true), [3, 2, 1, 0, 12]);
    }

    #[test]
    fn flight_node_columns_match_vanilla_server_output() {
        // Extracted with vanilla 26.3 Mth; negative diagonals distinguish floor from truncation.
        let expected = [
            (60, 0),
            (51, 30),
            (29, 51),
            (0, 60),
            (-31, 51),
            (-52, 29),
            (-60, 0),
            (-52, -31),
            (-30, -52),
            (0, -60),
            (29, -52),
            (51, -30),
            (40, 0),
            (28, 28),
            (0, 40),
            (-29, 28),
            (-40, 0),
            (-29, -29),
            (0, -40),
            (28, -29),
            (20, 0),
            (0, 20),
            (-20, 0),
            (0, -20),
        ];
        for (index, position) in expected.into_iter().enumerate() {
            assert_eq!(
                EnderDragonEntity::flight_node_horizontal_position(index),
                position,
                "flight node {index}",
            );
        }
    }

    #[test]
    fn nearest_flight_node_excludes_the_outer_ring_without_live_crystals() {
        let mut nodes = [None; NODE_COUNT];
        nodes[0] = Some(DragonNode::new(60.0, 73.0, 0.0));
        nodes[12] = Some(DragonNode::new(40.0, 175.0, 0.0));
        nodes[20] = Some(DragonNode::new(20.0, 165.0, 0.0));
        let pos = Vector3::new(60.5, 120.0, 0.5);
        assert_eq!(EnderDragonEntity::nearest_node_in(&nodes, pos, false), 12);
        assert_eq!(EnderDragonEntity::nearest_node_in(&nodes, pos, true), 0);
    }

    #[test]
    fn nearest_flight_node_floors_the_query_and_keeps_the_first_tie() {
        let mut nodes = [None; NODE_COUNT];
        nodes[12] = Some(DragonNode::new(-2.0, 73.0, 0.0));
        nodes[13] = Some(DragonNode::new(-1.0, 73.0, 0.0));
        assert_eq!(
            EnderDragonEntity::nearest_node_in(&nodes, Vector3::new(-1.1, 73.9, 0.9), false),
            12,
        );
        nodes[12] = Some(DragonNode::new(0.0, 73.0, 0.0));
        nodes[13] = Some(DragonNode::new(2.0, 73.0, 0.0));
        assert_eq!(
            EnderDragonEntity::nearest_node_in(&nodes, Vector3::new(1.9, 73.0, 0.0), false),
            12,
        );
    }

    #[test]
    fn nearest_flight_node_keeps_vanillas_strict_search_distance_limit() {
        let mut nodes = [None; NODE_COUNT];
        nodes[12] = Some(DragonNode::new(0.0, 73.0, 0.0));
        for (x, expected) in [(99.99, 12), (100.0, 0), (100.99, 0), (101.0, 0)] {
            assert_eq!(
                EnderDragonEntity::nearest_node_in(&nodes, Vector3::new(x, 73.0, 0.0), false),
                expected,
            );
        }
    }

    #[test]
    fn flight_reversals_take_the_negative_half_turn() {
        for yaw in [0.0, 360.0, -360.0] {
            assert_eq!(EnderDragonEntity::flight_turn_delta(0.0, 30.0, yaw), -50.0);
        }
        for yaw in [180.0, -180.0] {
            assert_eq!(EnderDragonEntity::flight_turn_delta(0.0, -30.0, yaw), -50.0);
        }
    }

    #[test]
    fn flight_turns_on_either_side_of_the_reversal_keep_their_direction() {
        assert_eq!(EnderDragonEntity::flight_turn_delta(0.0, 30.0, 1.0), 50.0);
        assert_eq!(EnderDragonEntity::flight_turn_delta(0.0, 30.0, -1.0), -50.0);
        assert_eq!(
            EnderDragonEntity::flight_turn_delta(0.0, -30.0, 10.0),
            -10.0
        );
        assert_eq!(
            EnderDragonEntity::flight_turn_delta(0.0, -30.0, -10.0),
            10.0
        );
        assert_eq!(EnderDragonEntity::flight_turn_delta(0.0, -30.0, 0.0), 0.0);
    }

    #[test]
    fn contact_damage_waits_three_ticks_after_any_living_attacker_hit() {
        for ticks in [0, 1, 2] {
            assert!(!EnderDragonEntity::can_damage_contact_victim(ticks));
        }
        for ticks in [3, 4, 100] {
            assert!(EnderDragonEntity::can_damage_contact_victim(ticks));
        }
    }

    #[test]
    fn contact_excludes_creative_and_spectator_players() {
        for gamemode in [GameMode::Creative, GameMode::Spectator] {
            assert!(!EnderDragonEntity::can_collide_with_player(gamemode, 0));
        }
        for gamemode in [GameMode::Survival, GameMode::Adventure] {
            assert!(EnderDragonEntity::can_collide_with_player(gamemode, 0));
        }
    }

    #[test]
    fn contact_resumes_on_the_tick_the_hurt_animation_expires() {
        for gamemode in [GameMode::Survival, GameMode::Adventure] {
            for hurt_time in 2..=10 {
                assert!(!EnderDragonEntity::can_collide_with_player(
                    gamemode, hurt_time
                ));
            }
            for hurt_time in [1, 0] {
                assert!(EnderDragonEntity::can_collide_with_player(
                    gamemode, hurt_time
                ));
            }
        }
        for gamemode in [GameMode::Creative, GameMode::Spectator] {
            for hurt_time in 0..=10 {
                assert!(!EnderDragonEntity::can_collide_with_player(
                    gamemode, hurt_time
                ));
            }
        }
    }

    #[test]
    fn contact_push_is_outward_and_decreases_with_distance() {
        let body = Vector3::new(8.0, 80.0, 7.0);
        for (target, expected) in [
            (
                Vector3::new(12.0, 80.0, 7.0),
                Vector3::new(1.0, f64::from(0.2f32), 0.0),
            ),
            (
                Vector3::new(16.0, 80.0, 7.0),
                Vector3::new(0.5, f64::from(0.2f32), 0.0),
            ),
            (
                Vector3::new(4.0, 80.0, 7.0),
                Vector3::new(-1.0, f64::from(0.2f32), 0.0),
            ),
            (
                Vector3::new(11.0, 86.0, 11.0),
                Vector3::new(0.48, f64::from(0.2f32), 0.64),
            ),
        ] {
            assert_eq!(EnderDragonEntity::knockback_push(body, target), expected);
        }
    }

    #[test]
    fn contact_push_clamps_distance_without_randomizing_the_center() {
        let body = Vector3::new(0.0, 80.0, 0.0);
        assert_eq!(
            EnderDragonEntity::knockback_push(body, Vector3::new(0.05, 80.0, -0.05)),
            Vector3::new(2.0, f64::from(0.2f32), -2.0),
        );
        assert_eq!(
            EnderDragonEntity::knockback_push(body, Vector3::new(0.0, 80.0, 0.0)),
            Vector3::new(0.0, f64::from(0.2f32), 0.0),
        );
    }

    #[test]
    fn block_destruction_respects_mob_griefing() {
        assert!(EnderDragonEntity::can_destroy_block(&Block::STONE, true));
        assert!(!EnderDragonEntity::can_destroy_block(&Block::STONE, false));
    }

    #[test]
    fn block_destruction_preserves_immune_and_transparent_blocks() {
        for block in [
            &Block::BARRIER,
            &Block::CRYING_OBSIDIAN,
            &Block::REINFORCED_DEEPSLATE,
            &Block::END_STONE,
            &Block::LIGHT,
            &Block::FIRE,
            &Block::AIR,
            &Block::CAVE_AIR,
        ] {
            assert!(
                !EnderDragonEntity::can_destroy_block(block, true),
                "dragon destroyed {}",
                block.name
            );
        }
    }
}
