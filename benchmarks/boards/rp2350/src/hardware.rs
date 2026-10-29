// SAFETY: This module owns startup peripherals, core counters and immutable Flash reads.
#![allow(unsafe_code)]

use core::fmt::Write;
use core::hint::black_box;

use heapless::String;
use rp235x_hal::{self as hal, Clock};
use usb_device::class_prelude::UsbBusAllocator;
use usb_device::prelude::*;

use crate::{measurements, telemetry};

#[unsafe(link_section = ".start_block")]
#[used]
static IMAGE_DEF: hal::block::ImageDef = hal::block::ImageDef::secure_exe();

#[hal::entry]
fn main() -> ! {
    if start().is_err() {
        hal::halt();
    }
    hal::halt()
}

fn start() -> Result<(), core::fmt::Error> {
    let mut dp = hal::pac::Peripherals::take().ok_or(core::fmt::Error)?;
    initialize_counter()?;
    let chip_id = dp.SYSINFO.chip_id().read().bits();
    let uid = device_uid()?;
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
    let bus = UsbBusAllocator::new(hal::usb::UsbBus::new(
        dp.USB,
        dp.USB_DPRAM,
        clocks.usb_clock,
        true,
        &mut dp.RESETS,
    ));
    let mut port = usbd_serial::SerialPort::new(&bus);
    let strings = [StringDescriptors::default()
        .manufacturer("Pow benchmark")
        .product("RP2350 pow validation")
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
    let sof_hz = usb_clock_check(hz, || {
        device.poll(&mut [&mut port]);
    })?;
    black_box(pow_bench_core::arithmetic_f32(
        black_box(1.25),
        black_box(0.75),
    ));
    let mut payload = measurements::Payload::new();
    if measurements::measure(&mut payload, hz, || {
        device.poll(&mut [&mut port]);
    })
    .is_err()
    {
        telemetry::serve(
            &mut port,
            &mut device,
            "{\"protocol\":\"POWBENCH/1\",\"state\":\"payload_overflow\"}\n",
            &[],
        );
    }
    let info = identity(chip_id, hz, sof_hz, &uid, payload.as_bytes())?;
    telemetry::serve(&mut port, &mut device, &info, payload.as_bytes());
}

#[cfg(target_arch = "arm")]
fn initialize_counter() -> Result<(), core::fmt::Error> {
    cortex_m::interrupt::disable();
    let mut cp = cortex_m::Peripherals::take().ok_or(core::fmt::Error)?;
    cp.DCB.enable_trace();
    cortex_m::peripheral::DWT::unlock();
    cp.DWT.enable_cycle_counter();
    if !cfg!(feature = "dcp") {
        // SAFETY: CP4 is the DCP. Denying access makes accidental use in the software build fault.
        unsafe {
            cp.SCB.cpacr.modify(|value| value & !(3 << 8));
        }
        cortex_m::asm::isb();
    }
    Ok(())
}

#[cfg(target_arch = "riscv32")]
fn initialize_counter() -> Result<(), core::fmt::Error> {
    // SAFETY: The benchmark owns machine-mode interrupt and counter configuration on core 0.
    unsafe {
        riscv::interrupt::disable();
        core::arch::asm!("csrci 0x320, 1", options(nomem, nostack));
    }
    Ok(())
}

#[cfg(target_arch = "arm")]
pub fn cycle_count() -> u32 {
    cortex_m::peripheral::DWT::cycle_count()
}

#[cfg(target_arch = "riscv32")]
pub fn cycle_count() -> u32 {
    riscv::register::mcycle::read() as u32
}

fn usb_clock_check(hz: u32, mut poll: impl FnMut()) -> Result<u32, core::fmt::Error> {
    // SAFETY: SOF_RD is a read-only register; the USB driver owns all USB writes.
    let frame = || unsafe { (*hal::pac::USB::ptr()).sof_rd().read().bits() & 0x7ff };
    let start = cycle_count();
    let initial = frame();
    while frame() == initial {
        poll();
        if cycle_count().wrapping_sub(start) > hz {
            return Err(core::fmt::Error);
        }
    }
    let first_frame = frame();
    let first_cycle = cycle_count();
    while frame().wrapping_sub(first_frame) & 0x7ff < 100 {
        poll();
        if cycle_count().wrapping_sub(first_cycle) > hz {
            return Err(core::fmt::Error);
        }
    }
    let cycles = cycle_count().wrapping_sub(first_cycle);
    let frames = frame().wrapping_sub(first_frame) & 0x7ff;
    let measured = (u64::from(cycles) * 1000 / u64::from(frames)) as u32;
    if measured.abs_diff(hz) > hz / 200 {
        return Err(core::fmt::Error);
    }
    Ok(measured)
}

fn device_uid() -> Result<String<16>, core::fmt::Error> {
    let chip = hal::rom_data::sys_info_api::chip_info()
        .map_err(|_| core::fmt::Error)?
        .ok_or(core::fmt::Error)?;
    let mut uid = String::new();
    write!(uid, "{:08x}{:08x}", chip.wafer_id, chip.device_id)?;
    Ok(uid)
}

fn identity(
    chip_id: u32,
    hz: u32,
    sof_hz: u32,
    uid: &str,
    payload: &[u8],
) -> Result<String<2048>, core::fmt::Error> {
    // SAFETY: Linker bounds enclose only this application's immutable Flash load image.
    unsafe extern "C" {
        static __flash_image_end: u8;
    }
    let flash = unsafe {
        let end = core::ptr::addr_of!(__flash_image_end) as usize;
        core::slice::from_raw_parts(0x10000000 as *const u8, end - 0x10000000)
    };
    let (fpscr, mvfr0, cpacr, misa) = processor_identity();
    // SAFETY: The benchmark only observes the XIP cache configuration established by the ROM.
    let xip_ctrl = unsafe { (*hal::pac::XIP_CTRL::ptr()).ctrl().read().bits() };
    let mode = if cfg!(target_arch = "riscv32") {
        "riscv"
    } else if cfg!(feature = "dcp") {
        "dcp"
    } else {
        "arm"
    };
    let mut info = String::new();
    writeln!(
        info,
        "{{\"protocol\":\"POWBENCH/1\",\"state\":\"complete\",\"run_id\":\"rp2350-{mode}-{uid}\",\"device_id\":\"{uid}\",\"chip_id\":{chip_id},\"clock_hz\":{hz},\"sof_clock_hz\":{sof_hz},\"mode\":\"{mode}\",\"fpscr\":{fpscr},\"mvfr0\":{mvfr0},\"cpacr\":{cpacr},\"misa\":{misa},\"xip_ctrl\":{xip_ctrl},\"rom_gitrev\":{},\"firmware_sha\":\"{}\",\"payload_sha256\":\"{}\",\"dataset_sha\":\"{}\"}}",
        hal::rom_data::git_revision(),
        telemetry::digest(flash)?,
        telemetry::digest(payload)?,
        include_str!("../../../vectors/timing.sha256").trim()
    )?;
    Ok(info)
}

#[cfg(target_arch = "arm")]
fn processor_identity() -> (u32, u32, u32, u32) {
    // SAFETY: These read-only accesses inspect the running core's floating-point configuration.
    unsafe {
        (
            cortex_m::register::fpscr::read().bits(),
            (*cortex_m::peripheral::FPU::PTR).mvfr[0].read(),
            (*cortex_m::peripheral::SCB::PTR).cpacr.read(),
            0,
        )
    }
}

#[cfg(target_arch = "riscv32")]
fn processor_identity() -> (u32, u32, u32, u32) {
    (
        0,
        0,
        0,
        riscv::register::misa::read().map_or(0, |value| value.bits() as u32),
    )
}
