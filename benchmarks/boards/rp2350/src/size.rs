//! Single-algorithm linked size fixture; not a telemetry or flashing image.
#![no_std]
#![no_main]

use core::hint::black_box;

use pow_bench_core::{DOMAINS, Implementation, Mode, cases, run};
use rp235x_hal::entry;

#[entry]
fn main() -> ! {
    #[cfg(feature = "size-candidate")]
    let implementation = Implementation::Candidate;
    #[cfg(not(feature = "size-candidate"))]
    let implementation = Implementation::Baseline;
    loop {
        for domain in DOMAINS {
            black_box(run(
                implementation,
                Mode::Throughput,
                cases(domain),
                1,
                domain.special,
            ));
        }
    }
}

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo<'_>) -> ! {
    rp235x_hal::halt()
}
