use std::hint::black_box;
use std::time::Instant;

const N: u32 = 2_000_000;

fn bench<F: Fn(f64, f64) -> f64>(name: &str, f: F) {
    let mut times = Vec::new();
    let mut checksum = 0.0;

    for _ in 0..7 {
        let t = Instant::now();
        checksum = black_box(powbench::run(N, &f));
        times.push(t.elapsed().as_secs_f64() * 1e9 / N as f64);
    }
    times.sort_by(f64::total_cmp);
    println!("{name:8} {:8.2} ns/op  sum={checksum:.9}",
             times[3]);
}

fn main() {
    bench("libm", libm::pow);
    bench("ARM", petir::fast_pow::powf_ieee);
    bench("std", |x, y| x.powf(y));
}
