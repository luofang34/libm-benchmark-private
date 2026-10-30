pub(crate) fn inputs(function: u32, domain: u32, count: usize) -> Vec<f64> {
    let mut state = 20261030u64;
    let factor = if function == 0 {
        std::f64::consts::LN_2
    } else {
        1.0
    };
    (0..count)
        .map(|index| {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let fraction = (state >> 11) as f64 / 9007199254740992.0;
            match domain {
                1 => (fraction - 0.5) * 1e-8,
                2 => f64::from_bits((state & 0xfffffffffffff) | ((state & 1) << 63) | 1),
                3 => (-1075.5 + 54.0 * fraction) * factor,
                4 => {
                    let edge = if index % 2 == 0 { 1024.0 } else { -1075.0 };
                    (edge + (fraction - 0.5) * 1e-9) * factor
                }
                5 => special(index % 8),
                _ => (-16.0 + 32.0 * fraction) * factor,
            }
        })
        .collect()
}

fn special(index: usize) -> f64 {
    match index {
        0 => 0.0,
        1 => -0.0,
        2 => f64::INFINITY,
        3 => f64::NEG_INFINITY,
        4 => f64::NAN,
        5 => f64::from_bits(0x7ff0000000000001),
        6 => f64::MAX,
        _ => -f64::MAX,
    }
}
