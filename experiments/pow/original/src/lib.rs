pub fn run<F: Fn(f64, f64) -> f64>(n: u32, f: F) -> f64 {
    let mut s = 2026_u64;
    let mut sum = 0.0;
    const SCALE: f64 = 1.0 / 9007199254740992.0;

    for _ in 0..n {
        s = s.wrapping_mul(6364136223846793005)
             .wrapping_add(1442695040888963407);
        let u = (s >> 11) as f64 * SCALE;
        let v = (s.rotate_left(29) >> 11) as f64 * SCALE;
        let x = 0.5 + 1.5 * u;
        let y = -8.0 + 16.0 * v;
        sum += f(x, y);
    }
    sum
}

#[cfg(feature = "only-libm")]
#[no_mangle]
pub extern "C" fn bench_libm(n: u32) -> f64 {
    run(n, libm::pow)
}

#[cfg(feature = "only-arm")]
#[no_mangle]
pub extern "C" fn bench_arm(n: u32) -> f64 {
    run(n, petir::fast_pow::powf_ieee)
}

#[cfg(feature = "only-std")]
#[no_mangle]
pub extern "C" fn bench_std(n: u32) -> f64 {
    run(n, |x, y| x.powf(y))
}
