//! Single-algorithm linked size fixture; not a telemetry or flashing image.
#![no_std]
#![no_main]

use core::hint::black_box;

use esp_hal::main;
use pow_bench_core::{DOMAINS, Implementation, Mode, cases, run};

// SAFETY: The immutable descriptor is required by the ESP boot image format.
#[allow(unsafe_code)]
mod descriptor;

#[main]
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
    loop {
        core::hint::spin_loop();
    }
}
