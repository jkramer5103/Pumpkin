#[derive(Clone, Copy, Default, Debug)]
pub struct Sample {
    pub y: f64,
    pub y_rot: f32,
}

#[derive(Clone, Copy, Debug)]
pub struct DragonFlightHistory {
    samples: [Sample; 64],
    head: i32,
}

impl Default for DragonFlightHistory {
    fn default() -> Self {
        Self {
            samples: [Sample::default(); 64],
            head: -1,
        }
    }
}

impl DragonFlightHistory {
    pub const fn record(&mut self, y: f64, y_rot: f32) {
        let sample = Sample { y, y_rot };
        if self.head < 0 {
            self.samples = [sample; 64];
        }
        self.head += 1;
        if self.head >= 64 {
            self.head = 0;
        }
        self.samples[self.head as usize] = sample;
    }

    #[must_use]
    pub fn get(&self, offset: i32) -> Sample {
        if self.head < 0 {
            return Sample::default();
        }
        let mut index = (self.head - offset) & 63;
        if index < 0 {
            index += 64;
        }
        self.samples[index as usize]
    }
}

#[cfg(test)]
mod tests {
    use super::DragonFlightHistory;

    #[test]
    fn initial_part_history_uses_first_observation() {
        let mut history = DragonFlightHistory::default();
        history.record(100.0, 90.0);
        for delay in 0..64 {
            let sample = history.get(delay);
            assert_eq!(sample.y, 100.0, "initial height at delay {delay}");
            assert_eq!(sample.y_rot, 90.0, "initial yaw at delay {delay}");
        }

        history.record(101.0, 95.0);
        assert_eq!(history.get(0).y, 101.0);
        assert_eq!(history.get(0).y_rot, 95.0);
        for delay in 1..64 {
            let sample = history.get(delay);
            assert_eq!(sample.y, 100.0, "retained height at delay {delay}");
            assert_eq!(sample.y_rot, 90.0, "retained yaw at delay {delay}");
        }
    }

    #[test]
    fn wrapping_keeps_the_previous_63_observations() {
        let mut history = DragonFlightHistory::default();
        for tick in 0..65 {
            history.record(80.0 + f64::from(tick), 180.0 + tick as f32);
        }
        for delay in 0..64 {
            let sample = history.get(delay);
            assert_eq!(sample.y, 144.0 - f64::from(delay));
            assert_eq!(sample.y_rot, 244.0 - delay as f32);
        }
    }
}
