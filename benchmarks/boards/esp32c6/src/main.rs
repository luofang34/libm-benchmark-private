//! ESP32-C6 pow measurements with ROM software FP32 and FP64.
#![no_std]
#![no_main]

// SAFETY: The bootloader descriptor uses fixed sections and an exported immutable symbol.
#[allow(unsafe_code)]
mod descriptor;
mod hardware;
mod image;
mod measurements;
mod telemetry;

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo<'_>) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
