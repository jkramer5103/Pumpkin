use std::sync::{
    Mutex,
    atomic::{AtomicUsize, Ordering},
};

use pumpkin_util::math::position::BlockPos;
use rustc_hash::FxHashSet;

use crate::tick::{MAX_TICK_DELAY, OrderedTick, ScheduledTick};

pub struct ChunkTickScheduler<T> {
    inner: Mutex<Option<Box<ChunkTickSchedulerInner<T>>>>,
    // The last completed step, rather than the next bucket to drain.
    offset: AtomicUsize,
}

struct ChunkTickSchedulerInner<T> {
    tick_queue: [Vec<OrderedTick<T>>; MAX_TICK_DELAY],
    queued_ticks: FxHashSet<(BlockPos, T)>,
}

impl<'a, T: std::hash::Hash + Eq> ChunkTickScheduler<&'a T> {
    pub fn step_tick(&self) -> Vec<OrderedTick<&'a T>> {
        let mut inner_guard = self
            .inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        // Vanilla advances game time before collecting scheduled ticks. Keep
        // the cursor and queue under the same lock so scheduling sees one step.
        let current_offset = (self.offset.load(Ordering::SeqCst) + 1) % MAX_TICK_DELAY;
        self.offset.store(current_offset, Ordering::SeqCst);
        let Some(inner) = inner_guard.as_mut() else {
            return Vec::new();
        };

        let res = std::mem::take(&mut inner.tick_queue[current_offset]);

        if !res.is_empty() {
            for next_tick in &res {
                inner
                    .queued_ticks
                    .remove(&(next_tick.position, next_tick.value));
            }
            if inner.queued_ticks.is_empty() {
                *inner_guard = None;
            }
        }
        res
    }

    pub fn schedule_tick(&self, tick: &ScheduledTick<&'a T>, sub_tick_order: u64) {
        let mut inner_guard = self
            .inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let offset = self.offset.load(Ordering::SeqCst);
        let inner = inner_guard.get_or_insert_with(|| {
            Box::new(ChunkTickSchedulerInner {
                tick_queue: std::array::from_fn(|_| Vec::new()),
                queued_ticks: FxHashSet::default(),
            })
        });

        if inner.queued_ticks.insert((tick.position, tick.value)) {
            // An already-due tick is collected on the next step, not after a
            // full rotation through the ring.
            let index = (offset + usize::from(tick.delay.max(1))) % MAX_TICK_DELAY;

            inner.tick_queue[index].push(OrderedTick {
                priority: tick.priority,
                sub_tick_order,
                position: tick.position,
                value: tick.value,
            });
        }
    }

    pub fn is_scheduled(&self, pos: BlockPos, value: &T) -> bool {
        self.inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .as_ref()
            .is_some_and(|inner| inner.queued_ticks.contains(&(pos, value)))
    }

    pub fn clear_area(&self, min: &BlockPos, max: &BlockPos) {
        let mut inner_guard = self
            .inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let Some(inner) = inner_guard.as_mut() else {
            return;
        };

        let contains = |position: &BlockPos| {
            position.0.x >= min.0.x
                && position.0.x < max.0.x
                && position.0.y >= min.0.y
                && position.0.y < max.0.y
                && position.0.z >= min.0.z
                && position.0.z < max.0.z
        };

        for queue in &mut inner.tick_queue {
            queue.retain(|tick| !contains(&tick.position));
        }
        inner
            .queued_ticks
            .retain(|(position, _)| !contains(position));
        let became_empty = inner.queued_ticks.is_empty();

        if became_empty {
            *inner_guard = None;
        }
    }

    pub fn has_ticks(&self) -> bool {
        self.inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .as_ref()
            .is_some_and(|inner| !inner.queued_ticks.is_empty())
    }

    #[must_use]
    pub fn to_vec(&self) -> Vec<ScheduledTick<&'a T>> {
        let inner_guard = self
            .inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let offset = self.offset.load(Ordering::SeqCst);
        let Some(inner) = inner_guard.as_ref() else {
            return Vec::new();
        };

        let mut res = Vec::new();

        for i in 0..MAX_TICK_DELAY {
            let index = (offset + i) % MAX_TICK_DELAY;
            res.extend(inner.tick_queue[index].iter().map(|x| ScheduledTick {
                delay: i as u8,
                priority: x.priority,
                position: x.position,
                value: x.value,
            }));
        }
        res
    }
}

impl<'a, T: std::hash::Hash + Eq + 'static> FromIterator<ScheduledTick<&'a T>>
    for ChunkTickScheduler<&'a T>
{
    fn from_iter<I: IntoIterator<Item = ScheduledTick<&'a T>>>(iter: I) -> Self {
        let scheduler = Self::default();
        let iter = iter.into_iter();

        let (lower, _) = iter.size_hint();
        if lower > 0 {
            let mut inner_guard = scheduler
                .inner
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            let inner = inner_guard.get_or_insert_with(|| {
                Box::new(ChunkTickSchedulerInner {
                    tick_queue: std::array::from_fn(|_| Vec::new()),
                    queued_ticks: FxHashSet::default(),
                })
            });
            inner.queued_ticks.reserve(lower);
        }

        for tick in iter {
            scheduler.schedule_tick(&tick, 0);
        }
        scheduler
    }
}

impl<T> Default for ChunkTickScheduler<T> {
    fn default() -> Self {
        Self {
            inner: Mutex::new(None),
            offset: AtomicUsize::new(0),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::ChunkTickScheduler;
    use crate::tick::{ScheduledTick, TickPriority};
    use pumpkin_util::math::position::BlockPos;

    const VALUE: &u8 = &0;

    fn tick(delay: u8) -> ScheduledTick<&'static u8> {
        ScheduledTick {
            delay,
            priority: TickPriority::Normal,
            position: BlockPos::new(2, 65, 2),
            value: VALUE,
        }
    }

    #[test]
    fn scheduled_ticks_fire_on_the_requested_step() {
        for delay in [0, 1, 2, 4, 5, 255] {
            let scheduler = ChunkTickScheduler::default();
            scheduler.schedule_tick(&tick(delay), 7);
            for step in 1..=u16::from(delay.max(1)) {
                let due = scheduler.step_tick();
                if step < u16::from(delay.max(1)) {
                    assert!(due.is_empty(), "delay {delay} fired on step {step}");
                } else {
                    assert_eq!(due.len(), 1, "delay {delay} missing on step {step}");
                    assert_eq!(due[0].sub_tick_order, 7);
                    assert_eq!(due[0].position, tick(delay).position);
                }
            }
            assert!(!scheduler.has_ticks());
            assert!(!scheduler.is_scheduled(tick(delay).position, VALUE));
        }
    }

    #[test]
    fn scheduled_ticks_keep_remaining_delay_across_save_and_wrap() {
        let scheduler = ChunkTickScheduler::default();
        for _ in 0..254 {
            assert!(scheduler.step_tick().is_empty());
        }
        scheduler.schedule_tick(&tick(5), 0);
        assert!(scheduler.step_tick().is_empty());
        assert!(scheduler.step_tick().is_empty());
        let saved = scheduler.to_vec();
        assert_eq!(saved.len(), 1);
        assert_eq!(saved[0].delay, 3);
        let loaded: ChunkTickScheduler<_> = saved.into_iter().collect();
        for current in [&scheduler, &loaded] {
            assert!(current.step_tick().is_empty());
            assert!(current.step_tick().is_empty());
            assert_eq!(current.step_tick().len(), 1);
            assert!(!current.has_ticks());
        }
    }

    #[test]
    fn callback_rescheduling_counts_from_the_completed_step() {
        let scheduler = ChunkTickScheduler::default();
        scheduler.schedule_tick(&tick(1), 0);
        assert_eq!(scheduler.step_tick().len(), 1);
        scheduler.schedule_tick(&tick(2), 1);
        // Duplicate scheduling cannot replace the original delay/order.
        scheduler.schedule_tick(&tick(1), 2);
        assert!(scheduler.step_tick().is_empty());
        let due = scheduler.step_tick();
        assert_eq!(due.len(), 1);
        assert_eq!(due[0].sub_tick_order, 1);
        assert!(!scheduler.has_ticks());
    }
}
