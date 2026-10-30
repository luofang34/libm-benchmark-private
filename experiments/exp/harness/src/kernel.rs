use std::hint::black_box;

/// Result of one complete in-runtime loop, including checksum accumulation.
#[repr(C)]
pub struct Measurement {
    /// Elapsed nanoseconds for the complete loop.
    pub ns: f64,
    /// Wrapping sum of every result's raw IEEE bits.
    pub checksum: u64,
    /// Number of mathematical function calls.
    pub calls: u64,
}

#[inline(never)]
fn exp(x: f64) -> f64 {
    #[cfg(feature = "direct-libm")]
    {
        libm::exp(x)
    }
    #[cfg(not(feature = "direct-libm"))]
    {
        x.exp()
    }
}
#[inline(never)]
fn exp2(x: f64) -> f64 {
    #[cfg(feature = "direct-libm")]
    {
        libm::exp2(x)
    }
    #[cfg(not(feature = "direct-libm"))]
    {
        x.exp2()
    }
}
#[inline(never)]
fn standard_exp(x: f64) -> f64 {
    x.exp()
}
#[inline(never)]
fn standard_exp2(x: f64) -> f64 {
    x.exp2()
}
#[inline(never)]
fn control(x: f64) -> f64 {
    x + 1.0
}

fn implementation(function: u32, kind: u32) -> fn(f64) -> f64 {
    match (function, kind) {
        (0, 0) => exp,
        (1, 0) => exp2,
        (0, 1) => standard_exp,
        (1, 1) => standard_exp2,
        _ => control,
    }
}

pub(crate) fn value(function: u32, kind: u32, x: f64) -> f64 {
    implementation(function, kind)(x)
}

pub(crate) fn measure(
    function: u32,
    kind: u32,
    mode: u32,
    domain: u32,
    repeats: u32,
) -> Measurement {
    // Allocation and PRNG work finish before either clock is sampled.
    let data = crate::inputs::inputs(function, domain, 16384);
    let operation = implementation(function, kind);
    #[cfg(not(target_arch = "wasm32"))]
    let start = std::time::Instant::now();
    #[cfg(target_arch = "wasm32")]
    let start = crate::abi::now();
    let checksum = if mode == 0 {
        throughput(&data, operation, repeats)
    } else {
        dependency(&data, operation, domain, repeats)
    };
    #[cfg(not(target_arch = "wasm32"))]
    let ns = start.elapsed().as_nanos() as f64;
    #[cfg(target_arch = "wasm32")]
    let ns = (crate::abi::now() - start) * 1e6;
    Measurement {
        ns,
        checksum: black_box(checksum),
        calls: data.len() as u64 * u64::from(repeats),
    }
}

fn throughput(data: &[f64], operation: fn(f64) -> f64, repeats: u32) -> u64 {
    let mut sums = [0u64; 4];
    for _ in 0..repeats {
        for row in data.as_chunks::<4>().0 {
            for index in 0..4 {
                let result = operation(black_box(row[index])).to_bits();
                sums[index] = sums[index].wrapping_add(result);
            }
        }
    }
    sums.iter().fold(0u64, |sum, bits| sum.wrapping_add(*bits))
}

fn dependency(data: &[f64], operation: fn(f64) -> f64, domain: u32, repeats: u32) -> u64 {
    let mut previous = 0u64;
    let mut sum = 0u64;
    for _ in 0..repeats {
        for (index, x) in data.iter().enumerate() {
            // Bounded bit feedback preserves each input distribution; special
            // values instead use an address dependency to retain their classes.
            let input = if domain == 5 {
                data[(index + ((previous >> 52) as usize & 15)) & (data.len() - 1)]
            } else {
                f64::from_bits(x.to_bits() ^ (previous & 255))
            };
            previous = operation(black_box(input)).to_bits();
            sum = sum.wrapping_add(previous);
        }
    }
    sum
}
