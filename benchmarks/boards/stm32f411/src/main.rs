//! STM32F411 USB FS firmware retaining paired pow measurements for host retrieval.
#![no_std]
#![no_main]

mod hardware;
mod measurements;
mod telemetry;

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo<'_>) -> ! {
    loop {
        cortex_m::asm::wfi();
    }
}
