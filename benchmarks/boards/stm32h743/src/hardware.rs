// SAFETY: This module owns the reset-time peripherals and the non-returning USB buffer frame.
#![allow(unsafe_code)]

use core::fmt::Write;

use cortex_m_rt::entry;
use heapless::String;
use stm32h7xx_hal::pac;
use stm32h7xx_hal::prelude::*;
use stm32h7xx_hal::rcc::rec::UsbClkSel;
use stm32h7xx_hal::usb_hs::{USB2, UsbBus};
use usb_device::prelude::*;

use crate::{measurements, telemetry};

#[entry]
fn main() -> ! {
    if start().is_err() {
        loop {
            cortex_m::asm::wfi();
        }
    }
    loop {
        cortex_m::asm::wfi();
    }
}

fn start() -> Result<(), core::fmt::Error> {
    let dp = pac::Peripherals::take().ok_or(core::fmt::Error)?;
    let mut cp = cortex_m::Peripherals::take().ok_or(core::fmt::Error)?;
    cortex_m::interrupt::disable();
    cp.SCB.enable_icache();
    // Preserve the bootloader's D-cache state and report the actual CCR with each capture.
    cp.DCB.enable_trace();
    cortex_m::peripheral::DWT::unlock();
    cp.DWT.enable_cycle_counter();
    let chip_id = dp.DBGMCU.idc.read().bits();
    let (usb, hz) = configure(dp);
    let mut ep_memory = [0u32; 1024];
    // SAFETY: The bus and all borrowers are dropped before this frame can return. This array
    // is never moved or accessed through another reference while the bus owns its storage.
    let memory = unsafe { &mut *(&mut ep_memory as *mut [u32; 1024]) };
    let bus = UsbBus::new(usb, memory);
    let mut port = usbd_serial::SerialPort::new(&bus);
    let strings = [usb_device::device::StringDescriptors::default()
        .manufacturer("Pow benchmark")
        .product("H743 pow validation")
        .serial_number("200364500000")];
    let mut device = UsbDeviceBuilder::new(&bus, UsbVidPid(0x16c0, 0x27dd))
        .strings(&strings)
        .map_err(|_| core::fmt::Error)?
        .device_class(usbd_serial::USB_CLASS_CDC)
        .build();
    while device.state() != UsbDeviceState::Configured {
        device.poll(&mut [&mut port]);
    }
    let mut payload = measurements::Payload::new();
    let measured = measurements::measure(&mut payload, hz, || {
        device.poll(&mut [&mut port]);
    });
    if measured.is_err() {
        telemetry::serve(
            &mut port,
            &mut device,
            "{\"protocol\":\"POWBENCH/1\",\"state\":\"payload_overflow\"}\n",
            &[],
        );
    }
    let info = identity(chip_id, hz, payload.as_bytes())?;
    telemetry::serve(&mut port, &mut device, &info, payload.as_bytes());
}

fn configure(dp: pac::Peripherals) -> (USB2, u32) {
    let vos = dp.PWR.constrain().vos1().freeze();
    let mut ccdr = dp.RCC.constrain().sys_ck(200.MHz()).freeze(vos, &dp.SYSCFG);
    ccdr.peripheral.kernel_usb_clk_mux(UsbClkSel::Hsi48);
    let usb_sync = if dp.DBGMCU.idc.read().bits() >> 16 <= 0x1003 {
        0
    } else {
        3
    };
    // SAFETY: CRS is exclusively owned here. USB2 SOF has different mux encodings on early silicon.
    unsafe {
        let rcc = &*pac::RCC::ptr();
        rcc.apb1henr.modify(|_, w| w.crsen().set_bit());
        dp.CRS.cfgr.modify(|_, w| {
            w.syncsrc()
                .bits(usb_sync)
                .reload()
                .bits(47999)
                .felim()
                .bits(34)
        });
        dp.CRS
            .cr
            .modify(|_, w| w.autotrimen().set_bit().cen().set_bit());
    }
    let gpio = dp.GPIOA.split(ccdr.peripheral.GPIOA);
    let hz = ccdr.clocks.sys_ck().raw();
    let usb = USB2::new(
        dp.OTG2_HS_GLOBAL,
        dp.OTG2_HS_DEVICE,
        dp.OTG2_HS_PWRCLK,
        gpio.pa11.into_alternate(),
        gpio.pa12.into_alternate(),
        ccdr.peripheral.USB2OTG,
        &ccdr.clocks,
    );
    (usb, hz)
}

fn identity(chip_id: u32, hz: u32, payload: &[u8]) -> Result<String<2048>, core::fmt::Error> {
    // SAFETY: Linker bounds enclose only the immutable load image in the device's internal Flash.
    unsafe extern "C" {
        static __flash_image_end: u8;
    }
    let flash = unsafe {
        let end = core::ptr::addr_of!(__flash_image_end) as usize;
        core::slice::from_raw_parts(0x08000000 as *const u8, end - 0x08000000)
    };
    let mut info = String::new();
    let mut uid = String::<24>::new();
    for b in stm32h7xx_hal::signature::Uid::read() {
        write!(uid, "{b:02x}")?;
    }
    let fpscr = cortex_m::register::fpscr::read().bits();
    // SAFETY: These read-only feature/control fields belong to the core running this firmware.
    let (mvfr0, ccr) = unsafe {
        (
            (*cortex_m::peripheral::FPU::PTR).mvfr[0].read(),
            (*cortex_m::peripheral::SCB::PTR).ccr.read(),
        )
    };
    writeln!(
        info,
        "{{\"protocol\":\"POWBENCH/1\",\"state\":\"complete\",\"run_id\":\"h743-{uid}\",\"device_id\":\"{uid}\",\"chip_id\":{chip_id},\"clock_hz\":{hz},\"fpscr\":{fpscr},\"mvfr0\":{mvfr0},\"scb_ccr\":{ccr},\"flash_kib\":{},\"firmware_sha\":\"{}\",\"payload_sha256\":\"{}\",\"dataset_sha\":\"{}\"}}",
        stm32h7xx_hal::signature::FlashSize::kilo_bytes(),
        telemetry::digest(flash)?,
        telemetry::digest(payload)?,
        include_str!("../../../vectors/timing.sha256").trim()
    )?;
    Ok(info)
}
