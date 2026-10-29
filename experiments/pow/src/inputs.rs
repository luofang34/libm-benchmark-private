pub const DOMAIN_NAMES: [&str; 6] = [
    "positive",
    "near_one",
    "negative_integer",
    "subnormal",
    "range_edge",
    "special",
];

pub fn inputs(domain: u32, count: usize) -> Vec<(f64, f64)> {
    let mut state = 2026u64;
    (0..count)
        .map(|i| {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let u = (state >> 11) as f64 / 9007199254740992.0;
            let v = (state.rotate_left(29) >> 11) as f64 / 9007199254740992.0;
            match domain {
                1 => (1.0 + (u - 0.5) * 2e-8, (v - 0.5) * 2e10),
                2 => (-0.5 - 1.5 * u, (v * 33.0) as i32 as f64 - 16.0),
                3 => (f64::from_bits((state & 0xfffffffffffff) | 1), 0.2 + 1.3 * v),
                4 => (
                    2.0 + (u - 0.5) * 1e-12,
                    if i % 2 == 0 {
                        1024.0 + (v - 0.5) * 1e-9
                    } else {
                        -1075.0 + (v - 0.5) * 1e-9
                    },
                ),
                5 => special(i % 16),
                _ => (0.5 + 1.5 * u, -8.0 + 16.0 * v),
            }
        })
        .collect()
}

fn special(i: usize) -> (f64, f64) {
    match i {
        0 => (0.0, 3.0),
        1 => (-0.0, 3.0),
        2 => (-0.0, -3.0),
        3 => (f64::INFINITY, -2.5),
        4 => (f64::NEG_INFINITY, 3.0),
        5 => (f64::NAN, 0.0),
        6 => (1.0, f64::NAN),
        7 => (f64::NAN, 2.0),
        8 => (-1.0, f64::INFINITY),
        9 => (0.5, f64::NEG_INFINITY),
        10 => (2.0, f64::INFINITY),
        11 => (-2.0, 0.5),
        12 => (0.0, -1.0),
        13 => (1.0, 2.5),
        14 => (-1.0, 9007199254740992.0),
        _ => (2.0, 0.0),
    }
}
