//! RP2350 pow measurements with separately identified Arm, Hazard3 and DCP builds.
#![no_std]
#![no_main]

mod hardware;
mod measurements;
mod telemetry;

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo<'_>) -> ! {
    rp235x_hal::halt()
}
