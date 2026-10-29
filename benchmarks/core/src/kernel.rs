use core::hint::black_box;

use crate::Case;

/// Mathematical implementation under test, independent of the board runtime.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Implementation {
    /// fdlibm algorithm from the pinned upstream revision.
    Baseline,
    /// Portable Arm table-driven algorithm without an explicit FMA.
    Candidate,
}

/// Timing kernel; dependency includes the cost of feedback between calls.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    /// Four accumulation lanes over independent input pairs.
    Throughput,
    /// Low output bits affect the following base while preserving its exponent.
    Dependency,
}

/// Consumed output and exact operation count, with no timer or telemetry overhead.
#[derive(Debug, PartialEq, Eq)]
pub struct Outcome {
    /// Wrapping sum of all result bit patterns.
    pub checksum: u64,
    /// Number of pow evaluations.
    pub calls: u64,
}

/// Evaluate one pair for the separate accuracy pass.
pub fn value(implementation: Implementation, x: f64, y: f64) -> f64 {
    match implementation {
        Implementation::Baseline => baseline_pow(x, y),
        Implementation::Candidate => candidate_pow(x, y),
    }
}

#[inline(never)]
fn baseline_pow(x: f64, y: f64) -> f64 {
    baseline::pow(x, y)
}

#[inline(never)]
fn candidate_pow(x: f64, y: f64) -> f64 {
    candidate::pow(x, y)
}

/// Run one batch. Special-value domains use output-dependent indexing to preserve NaNs/zeros.
/// Dispatch happens once per batch. Callers must time only this function.
pub fn run(
    implementation: Implementation,
    mode: Mode,
    data: &[Case],
    repeats: u32,
    special: bool,
) -> Outcome {
    match implementation {
        Implementation::Baseline => kernel(mode, data, repeats, special, baseline_pow),
        Implementation::Candidate => kernel(mode, data, repeats, special, candidate_pow),
    }
}

fn kernel(
    mode: Mode,
    data: &[Case],
    repeats: u32,
    special: bool,
    pow: impl Fn(f64, f64) -> f64,
) -> Outcome {
    let mut sums = [0u64; 4];
    let mut previous = 0u64;
    for _ in 0..repeats {
        for (i, &case) in data.iter().enumerate() {
            let pair = match (mode, special) {
                (Mode::Dependency, true) => data[(i + (previous as usize & 15)) % data.len()],
                (Mode::Dependency, false) => Case {
                    x: case.x ^ (previous & 255),
                    y: case.y,
                },
                (Mode::Throughput, _) => case,
            };
            let pair = black_box(pair);
            previous = pow(f64::from_bits(pair.x), f64::from_bits(pair.y)).to_bits();
            sums[i % 4] = sums[i % 4].wrapping_add(previous);
        }
    }
    Outcome {
        checksum: black_box(sums.into_iter().fold(0u64, u64::wrapping_add)),
        calls: (data.len() as u64) * u64::from(repeats),
    }
}

/// Arithmetic code-generation probe; it does not imply a verified physical FPU.
#[inline(never)]
pub fn arithmetic_f32(x: f32, y: f32) -> f32 {
    x * y + x / y
}

/// Arithmetic code-generation probe for hardware FP64 versus runtime helpers.
#[inline(never)]
pub fn arithmetic_f64(x: f64, y: f64) -> f64 {
    x * y + x / y
}

#[cfg(test)]
mod tests;
