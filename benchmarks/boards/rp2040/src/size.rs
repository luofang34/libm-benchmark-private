//! Single-algorithm linked size fixture; not a telemetry or flashing image.
#![no_std]
#![no_main]

use core::hint::black_box;

use pow_bench_core::{DOMAINS, Implementation, Mode, cases, run};
use rp2040_hal::entry;

// SAFETY: The boot module contains only the required linker-placed ROM boot block.
#[allow(unsafe_code)]
#[path = "hardware/boot.rs"]
mod boot;

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
    cortex_m::asm::udf()
}
