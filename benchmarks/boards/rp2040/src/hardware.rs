// SAFETY: This module owns boot state, device registers, counters and immutable Flash reads.
#![allow(unsafe_code)]

use core::fmt::Write;
use core::hint::black_box;

use heapless::String;
use rp2040_hal::{self as hal, Clock};
use usb_device::class_prelude::UsbBusAllocator;
use usb_device::prelude::*;

use crate::{measurements, telemetry};

mod boot;

#[hal::entry]
fn main() -> ! {
    if start().is_err() {
        cortex_m::asm::udf();
    }
    cortex_m::asm::udf()
}

fn start() -> Result<(), core::fmt::Error> {
    cortex_m::interrupt::disable();
    let mut dp = hal::pac::Peripherals::take().ok_or(core::fmt::Error)?;
    initialize_counter()?;
    let chip_id = dp.SYSINFO.chip_id().read().bits();
    let (jedec, uid) = flash_identity()?;
    let mut watchdog = hal::Watchdog::new(dp.WATCHDOG);
    let clocks = hal::clocks::init_clocks_and_plls(
        12_000_000,
        dp.XOSC,
        dp.CLOCKS,
        dp.PLL_SYS,
        dp.PLL_USB,
        &mut dp.RESETS,
        &mut watchdog,
    )
    .map_err(|_| core::fmt::Error)?;
    let hz = clocks.system_clock.freq().to_Hz();
    let timer = hal::Timer::new(dp.TIMER, &mut dp.RESETS, &clocks);
    let bus = UsbBusAllocator::new(hal::usb::UsbBus::new(
        dp.USBCTRL_REGS,
        dp.USBCTRL_DPRAM,
        clocks.usb_clock,
        true,
        &mut dp.RESETS,
    ));
    let mut port = usbd_serial::SerialPort::new(&bus);
    let strings = [StringDescriptors::default()
        .manufacturer("Pow benchmark")
        .product("RP2040 pow validation")
        .serial_number(&uid)];
    let mut device = UsbDeviceBuilder::new(&bus, UsbVidPid(0x16c0, 0x27dd))
        .strings(&strings)
        .map_err(|_| core::fmt::Error)?
        .max_packet_size_0(64)
        .map_err(|_| core::fmt::Error)?
        .device_class(usbd_serial::USB_CLASS_CDC)
        .build();
    while device.state() != UsbDeviceState::Configured {
        device.poll(&mut [&mut port]);
    }
    let sof_hz = usb_clock_check(hz, &timer, || {
        device.poll(&mut [&mut port]);
    })?;
    black_box(pow_bench_core::arithmetic_f32(
        black_box(1.25),
        black_box(0.75),
    ));
    let mut payload = measurements::Payload::new();
    let maximum = match measurements::measure(&mut payload, hz, &timer, || {
        device.poll(&mut [&mut port]);
    }) {
        Ok(maximum) => maximum,
        Err(_) => telemetry::serve(
            &mut port,
            &mut device,
            "{\"protocol\":\"POWBENCH/1\",\"state\":\"measurement_or_buffer_error\"}\n",
            &[],
        ),
    };
    let info = identity(
        chip_id,
        jedec,
        hz,
        sof_hz,
        maximum,
        &uid,
        payload.as_bytes(),
    )?;
    telemetry::serve(&mut port, &mut device, &info, payload.as_bytes());
}

fn initialize_counter() -> Result<(), core::fmt::Error> {
    let mut cp = cortex_m::Peripherals::take().ok_or(core::fmt::Error)?;
    cp.SYST.disable_interrupt();
    cp.SYST
        .set_clock_source(cortex_m::peripheral::syst::SystClkSource::Core);
    cp.SYST.set_reload(0x00ff_ffff);
    cp.SYST.clear_current();
    cp.SYST.enable_counter();
    Ok(())
}

pub fn cycle_count() -> u32 {
    0x00ff_ffff - cortex_m::peripheral::SYST::get_current()
}

pub fn elapsed(start: u32) -> u32 {
    cycle_count().wrapping_sub(start) & 0x00ff_ffff
}

fn usb_clock_check(
    hz: u32,
    timer: &hal::Timer,
    mut poll: impl FnMut(),
) -> Result<u32, core::fmt::Error> {
    // SAFETY: SOF_RD is read-only; the USB driver owns writes to the controller.
    let frame = || unsafe { (*hal::pac::USBCTRL_REGS::ptr()).sof_rd().read().bits() & 0x7ff };
    let start = timer.get_counter_low();
    let initial = frame();
    while frame() == initial {
        poll();
        if timer.get_counter_low().wrapping_sub(start) > 1_000_000 {
            return Err(core::fmt::Error);
        }
    }
    let first_frame = frame();
    let first_cycle = cycle_count();
    let first_time = timer.get_counter_low();
    while frame().wrapping_sub(first_frame) & 0x7ff < 50 {
        poll();
        if timer.get_counter_low().wrapping_sub(first_time) > 100_000 {
            return Err(core::fmt::Error);
        }
    }
    let cycles = elapsed(first_cycle);
    let frames = frame().wrapping_sub(first_frame) & 0x7ff;
    let measured = (u64::from(cycles) * 1000 / u64::from(frames)) as u32;
    if measured.abs_diff(hz) > hz / 200 {
        return Err(core::fmt::Error);
    }
    Ok(measured)
}

fn flash_identity() -> Result<(u32, String<32>), core::fmt::Error> {
    // SAFETY: Core 1 is parked in ROM, interrupts are disabled, and no DMA is configured.
    // The driver executes in SRAM and restores the same generic boot2 XIP configuration.
    let jedec = unsafe { rp2040_flash::flash::flash_jedec_id(true) };
    let mut uid = String::new();
    let length = match jedec >> 16 {
        0xef => 8,
        0xba => 16,
        _ => {
            write!(uid, "jedec-{jedec:06x}")?;
            return Ok((jedec, uid));
        }
    };
    let mut bytes = [0u8; 16];
    // SAFETY: The Flash access exclusion above remains in effect; only the read-ID command runs.
    unsafe {
        rp2040_flash::flash::flash_unique_id(&mut bytes[..length], true);
    }
    for byte in &bytes[..length] {
        write!(uid, "{byte:02x}")?;
    }
    Ok((jedec, uid))
}

fn identity(
    chip_id: u32,
    jedec: u32,
    hz: u32,
    sof_hz: u32,
    maximum: u32,
    uid: &str,
    payload: &[u8],
) -> Result<String<2048>, core::fmt::Error> {
    unsafe extern "C" {
        static __flash_image_end: u8;
    }
    // SAFETY: Linker bounds enclose the immutable Flash load image, including SRAM load bytes.
    let flash = unsafe {
        let end = core::ptr::addr_of!(__flash_image_end) as usize;
        core::slice::from_raw_parts(0x10000000 as *const u8, end - 0x10000000)
    };
    // SAFETY: Only read-only inspection of cache, SPI and processor configuration occurs here.
    let (cpuid, syst_csr, xip_ctrl, spi_baud, spi_ctrl) = unsafe {
        (
            (*cortex_m::peripheral::CPUID::PTR).base.read(),
            (*cortex_m::peripheral::SYST::PTR).csr.read(),
            (*hal::pac::XIP_CTRL::ptr()).ctrl().read().bits(),
            (*hal::pac::XIP_SSI::ptr()).baudr().read().bits(),
            (*hal::pac::XIP_SSI::ptr()).spi_ctrlr0().read().bits(),
        )
    };
    let mut info = String::new();
    writeln!(
        info,
        "{{\"protocol\":\"POWBENCH/1\",\"state\":\"complete\",\"run_id\":\"rp2040-{uid}\",\"device_id\":\"{uid}\",\"chip_id\":{chip_id},\"flash_jedec\":{jedec},\"cpuid\":{cpuid},\"clock_hz\":{hz},\"sof_clock_hz\":{sof_hz},\"systick_csr\":{syst_csr},\"max_batch_us\":{maximum},\"xip_ctrl\":{xip_ctrl},\"spi_baud\":{spi_baud},\"spi_ctrl\":{spi_ctrl},\"rom_version\":{},\"firmware_sha\":\"{}\",\"payload_sha256\":\"{}\",\"dataset_sha\":\"{}\"}}",
        hal::rom_data::rom_version_number(),
        telemetry::digest(flash)?,
        telemetry::digest(payload)?,
        include_str!("../../../vectors/timing.sha256").trim()
    )?;
    Ok(info)
}
