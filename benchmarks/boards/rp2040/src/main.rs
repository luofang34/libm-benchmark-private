//! RP2040 pow measurements using compiler-provided software FP32 and FP64.
#![no_std]
#![no_main]

mod hardware;
mod measurements;
mod telemetry;

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo<'_>) -> ! {
    cortex_m::asm::udf()
}
