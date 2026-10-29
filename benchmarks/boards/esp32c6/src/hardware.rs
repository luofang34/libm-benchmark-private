// SAFETY: This module owns startup, privileged counters and read-only device registers.
#![allow(unsafe_code)]

use core::{arch::asm, fmt::Write, hint::black_box};

use esp_hal::{
    clock::{Clocks, CpuClock},
    efuse::Efuse,
    time::Instant,
    usb_serial_jtag::UsbSerialJtag,
};
use heapless::String;

use crate::{image, measurements, telemetry};

#[esp_hal::main]
fn main() -> ! {
    if start().is_err() {
        loop {
            core::hint::spin_loop();
        }
    }
    loop {
        core::hint::spin_loop();
    }
}

fn start() -> Result<(), core::fmt::Error> {
    let peripherals = esp_hal::init(esp_hal::Config::default().with_cpu_clock(CpuClock::_160MHz));
    initialize_counter();
    let mut port = UsbSerialJtag::new(peripherals.USB_DEVICE);
    let mut flash = esp_storage::FlashStorage::new(peripherals.FLASH);
    let (hash, bytes) = image::fingerprint_blocking(&mut flash)?;
    let hz = Clocks::get().cpu_clock.as_hz();
    let checked_hz = clock_check(hz)?;
    black_box(pow_bench_core::arithmetic_f32(
        black_box(1.25),
        black_box(0.75),
    ));
    let mut payload = measurements::Payload::new();
    let maximum = match measurements::measure(&mut payload, hz, || {}) {
        Ok(maximum) => maximum,
        Err(_) => telemetry::serve(
            &mut port,
            "{\"protocol\":\"POWBENCH/1\",\"state\":\"measurement_or_buffer_error\"}\n",
            &[],
        ),
    };
    let info = identity(hz, checked_hz, maximum, &hash, bytes, payload.as_bytes())?;
    telemetry::serve(&mut port, &info, payload.as_bytes());
}

fn initialize_counter() {
    // SAFETY: Only the active HP hart runs this program; no interrupt handlers are needed.
    // MPCER selects clock cycles, and MPCMR enables wrapping rather than saturation.
    unsafe {
        asm!("csrci mstatus, 8", "csrw 0x7e0, {one}", "csrw 0x7e1, {one}",
        "csrw 0x7e2, zero", one = in(reg) 1u32, options(nostack));
    }
}

#[inline]
pub fn cycle_count() -> u32 {
    let value;
    // SAFETY: MPCCR is a read-only access to the configured performance counter.
    unsafe {
        asm!("csrr {value}, 0x7e2", value = out(reg) value, options(nostack));
    }
    value
}

pub fn elapsed(start: u32) -> u32 {
    cycle_count().wrapping_sub(start)
}
pub fn micros() -> u32 {
    Instant::now().duration_since_epoch().as_micros() as u32
}

fn clock_check(hz: u32) -> Result<u32, core::fmt::Error> {
    let before = micros();
    let start = cycle_count();
    while micros().wrapping_sub(before) < 10_000 {
        core::hint::spin_loop();
    }
    let cycles = elapsed(start);
    let duration = micros().wrapping_sub(before);
    let measured = (u64::from(cycles) * 1_000_000 / u64::from(duration)) as u32;
    if measured.abs_diff(hz) > hz / 200 {
        return Err(core::fmt::Error);
    }
    Ok(measured)
}

fn identity(
    hz: u32,
    checked_hz: u32,
    maximum: u32,
    hash: &str,
    bytes: u32,
    payload: &[u8],
) -> Result<String<2048>, core::fmt::Error> {
    let mut uid = String::<12>::new();
    for byte in Efuse::read_base_mac_address() {
        write!(uid, "{byte:02x}")?;
    }
    let (misa, mstatus, event, mode): (u32, u32, u32, u32);
    // SAFETY: CSR and SPI register reads do not modify hardware state.
    let (spi_ctrl, spi_clock, mspi_clock, sysclk, cache_ctrl) = unsafe {
        asm!("csrr {isa}, misa", "csrr {status}, mstatus", "csrr {event}, 0x7e0", "csrr {mode}, 0x7e1",
            isa = out(reg) misa, status = out(reg) mstatus, event = out(reg) event, mode = out(reg) mode,
            options(nostack));
        let spi = &*esp32c6::SPI0::ptr();
        (
            spi.ctrl().read().bits(),
            spi.clock().read().bits(),
            (*esp32c6::PCR::ptr()).mspi_clk_conf().read().bits(),
            (*esp32c6::PCR::ptr()).sysclk_conf().read().bits(),
            (*esp32c6::EXTMEM::ptr()).l1_icache_ctrl().read().bits(),
        )
    };
    let mut info = String::new();
    writeln!(
        info,
        "{{\"protocol\":\"POWBENCH/1\",\"state\":\"complete\",\"run_id\":\"esp32c6-{uid}\",\"device_id\":\"{uid}\",\"major_revision\":{},\"minor_revision\":{},\"misa\":{misa},\"mstatus\":{mstatus},\"counter_event\":{event},\"counter_mode\":{mode},\"clock_hz\":{hz},\"timer_clock_hz\":{checked_hz},\"max_batch_us\":{maximum},\"spi_ctrl\":{spi_ctrl},\"spi_clock\":{spi_clock},\"mspi_clock\":{mspi_clock},\"sysclk\":{sysclk},\"cache_ctrl\":{cache_ctrl},\"firmware_sha\":\"{hash}\",\"firmware_bytes\":{bytes},\"payload_sha256\":\"{}\",\"dataset_sha\":\"{}\"}}",
        Efuse::major_chip_version(),
        Efuse::minor_chip_version(),
        telemetry::digest(payload)?,
        include_str!("../../../vectors/timing.sha256").trim()
    )?;
    Ok(info)
}
