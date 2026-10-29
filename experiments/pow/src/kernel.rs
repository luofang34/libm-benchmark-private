use crate::inputs;
use std::hint::black_box;
pub const IMPLEMENTATIONS: [&str; 5] = ["libm_old", "petir", "std", "arm_patch", "control"];

pub struct Measurement {
    pub ns: f64,
    pub checksum: u64,
    pub calls: usize,
}

#[inline(never)]
fn old(x: f64, y: f64) -> f64 {
    libm_old::pow(x, y)
}
#[inline(never)]
fn arm(x: f64, y: f64) -> f64 {
    libm_new::pow(x, y)
}
#[inline(never)]
fn petir(x: f64, y: f64) -> f64 {
    petir::fast_pow::powf_ieee(x, y)
}
#[inline(never)]
fn standard(x: f64, y: f64) -> f64 {
    x.powf(y)
}
#[inline(never)]
fn control(x: f64, y: f64) -> f64 {
    x + y
}

pub fn value(kind: u32, x: f64, y: f64) -> f64 {
    match kind {
        0 => old(x, y),
        1 => petir(x, y),
        2 => standard(x, y),
        3 => arm(x, y),
        _ => control(x, y),
    }
}

pub fn measure(kind: u32, mode: u32, domain: u32, repeats: u32) -> Measurement {
    let data = inputs(domain, 16384);
    match kind {
        0 => timed(&data, old, mode, domain, repeats),
        1 => timed(&data, petir, mode, domain, repeats),
        2 => timed(&data, standard, mode, domain, repeats),
        3 => timed(&data, arm, mode, domain, repeats),
        _ => timed(&data, control, mode, domain, repeats),
    }
}

fn timed(
    data: &[(f64, f64)],
    f: impl Fn(f64, f64) -> f64,
    mode: u32,
    domain: u32,
    repeats: u32,
) -> Measurement {
    #[cfg(not(target_arch = "wasm32"))]
    let start = std::time::Instant::now();
    #[cfg(target_arch = "wasm32")]
    let start = crate::abi::now();
    let checksum = if mode == 0 {
        throughput(data, f, repeats)
    } else {
        latency(data, f, domain, repeats)
    };
    #[cfg(not(target_arch = "wasm32"))]
    let ns = start.elapsed().as_nanos() as f64;
    #[cfg(target_arch = "wasm32")]
    let ns = (crate::abi::now() - start) * 1e6;
    Measurement {
        ns,
        checksum: black_box(checksum),
        calls: data.len() * repeats as usize,
    }
}

fn throughput(data: &[(f64, f64)], f: impl Fn(f64, f64) -> f64, repeats: u32) -> u64 {
    let mut sums = [0u64; 4];
    for _ in 0..repeats {
        for row in data.as_chunks::<4>().0 {
            for j in 0..4 {
                let (x, y) = black_box(row[j]);
                let bits = f(x, y).to_bits();
                sums[j] = sums[j].wrapping_add(bits);
            }
        }
    }
    sums.iter().fold(0u64, |acc, x| acc.wrapping_add(*x))
}

fn latency(data: &[(f64, f64)], f: impl Fn(f64, f64) -> f64, domain: u32, repeats: u32) -> u64 {
    let mut previous = 0u64;
    let mut sum = 0u64;
    for _ in 0..repeats {
        for (i, &(x, y)) in data.iter().enumerate() {
            let (base, exponent) = if domain == 5 {
                data[(i + ((previous >> 52) as usize & 15)) & (data.len() - 1)]
            } else {
                (f64::from_bits(x.to_bits() ^ (previous & 255)), y)
            };
            let (base, exponent) = black_box((base, exponent));
            previous = f(base, exponent).to_bits();
            sum = sum.wrapping_add(previous);
        }
    }
    sum
}
