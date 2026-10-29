// SAFETY: This module owns reset-time peripherals and bounded immutable device-memory reads.
#![allow(unsafe_code)]

use core::{fmt::Write, hint::black_box};
use cortex_m_rt::entry;
use heapless::String;
use stm32f4xx_hal::otg_fs::{USB, UsbBus};
use stm32f4xx_hal::rcc::Config;
use stm32f4xx_hal::{pac, prelude::*};
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
    cp.DCB.enable_trace();
    cp.DWT.enable_cycle_counter();
    let chip_id = dp.DBGMCU.idcode().read().bits();
    let (hse_hz, hse_estimate_hz) = measure_hse(&dp)?;
    let (usb, hz) = configure(dp, hse_hz);
    let uid = device_uid()?;
    let mut ep_memory = [0u32; 1024];
    // SAFETY: The bus and borrowers are dropped before this frame can return. The storage is
    // not moved or accessed through another reference during the bus lifetime.
    let memory = unsafe { &mut *(&mut ep_memory as *mut [u32; 1024]) };
    let bus = UsbBus::new(usb, memory);
    let mut port = usbd_serial::SerialPort::new(&bus);
    let strings = [StringDescriptors::default()
        .manufacturer("Pow benchmark")
        .product("F411 pow validation")
        .serial_number(&uid)];
    let mut device = UsbDeviceBuilder::new(&bus, UsbVidPid(0x16c0, 0x27dd))
        .strings(&strings)
        .map_err(|_| core::fmt::Error)?
        .device_class(usbd_serial::USB_CLASS_CDC)
        .build();
    while device.state() != UsbDeviceState::Configured {
        device.poll(&mut [&mut port]);
    }
    black_box(pow_bench_core::arithmetic_f32(
        black_box(1.25),
        black_box(0.75),
    ));
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
    let info = identity(
        chip_id,
        hz,
        &uid,
        payload.as_bytes(),
        hse_hz,
        hse_estimate_hz,
    )?;
    telemetry::serve(&mut port, &mut device, &info, payload.as_bytes());
}

fn configure(dp: pac::Peripherals, hse_hz: u32) -> (USB, u32) {
    let mut rcc = dp
        .RCC
        // 48 MHz supports every F411 voltage scale and gives an exact USB clock.
        .freeze(Config::hse(hse_hz.Hz()).sysclk(48.MHz()).require_pll48clk());
    let gpio = dp.GPIOA.split(&mut rcc);
    let hz = rcc.clocks.hclk().raw();
    let usb = USB::new(
        (dp.OTG_FS_GLOBAL, dp.OTG_FS_DEVICE, dp.OTG_FS_PWRCLK),
        (gpio.pa11, gpio.pa12),
        &rcc.clocks,
    );
    (usb, hz)
}

fn wait_ready(mut ready: impl FnMut() -> bool) -> Result<(), core::fmt::Error> {
    let start = cortex_m::peripheral::DWT::cycle_count();
    while !ready() {
        if cortex_m::peripheral::DWT::cycle_count().wrapping_sub(start) > 16_000_000 {
            return Err(core::fmt::Error);
        }
    }
    Ok(())
}

fn measure_hse(dp: &pac::Peripherals) -> Result<(u32, u32), core::fmt::Error> {
    dp.RCC.cr().modify(|_, w| w.hsion().set_bit());
    wait_ready(|| dp.RCC.cr().read().hsirdy().bit_is_set())?;
    dp.RCC.cfgr().modify(|_, w| w.sw().hsi());
    wait_ready(|| dp.RCC.cfgr().read().sws().is_hsi())?;
    // SAFETY: HSI is at 16 MHz, below the zero-wait-state Flash limit.
    dp.FLASH.acr().modify(|_, w| unsafe { w.latency().bits(0) });
    dp.RCC.cr().modify(|_, w| w.pllon().clear_bit());
    wait_ready(|| dp.RCC.cr().read().pllrdy().bit_is_clear())?;
    // SAFETY: RM0383 routes HSE/31 internally to TIM11, without configuring an external pin.
    dp.RCC.cfgr().modify(|_, w| unsafe {
        w.hpre()
            .div1()
            .ppre1()
            .div1()
            .ppre2()
            .div1()
            .rtcpre()
            .bits(31)
    });
    dp.RCC.cr().modify(|_, w| w.hseon().set_bit());
    wait_ready(|| dp.RCC.cr().read().hserdy().bit_is_set())?;
    dp.RCC.apb2enr().modify(|_, w| w.tim11en().set_bit());
    dp.RCC.apb2rstr().modify(|_, w| w.tim11rst().set_bit());
    dp.RCC.apb2rstr().modify(|_, w| w.tim11rst().clear_bit());
    let timer = &dp.TIM11;
    // SAFETY: The timer is exclusively owned. Max ARR avoids capture wrap ambiguity; each
    // capture spans eight HSE/31 edges to leave enough time for polling at 16 MHz HSI.
    unsafe {
        timer.arr().write(|w| w.arr().bits(65535));
        timer.or().write(|w| w.rmp().bits(2));
        timer
            .ccmr1_input()
            .write(|w| w.cc1s().ti1().ic1psc().bits(3));
    }
    timer.ccer().write(|w| w.cc1e().set_bit());
    timer.cr1().write(|w| w.cen().set_bit());
    let mut previous = capture(timer)?;
    let mut ticks = 0u32;
    for _ in 0..256 {
        let next = capture(timer)?;
        ticks = ticks.wrapping_add(u32::from(next.wrapping_sub(previous)));
        previous = next;
    }
    timer.cr1().write(|w| w.cen().clear_bit());
    dp.RCC.apb2enr().modify(|_, w| w.tim11en().clear_bit());
    if ticks == 0 {
        return Err(core::fmt::Error);
    }
    let estimated = (16_000_000u64 * 31 * 8 * 256 / u64::from(ticks)) as u32;
    let nominal = ((estimated + 500_000) / 1_000_000) * 1_000_000;
    // USB DFU on this family supports integer-MHz crystals. Reject ambiguous measurements.
    if !(4_000_000..=26_000_000).contains(&nominal) || estimated.abs_diff(nominal) > nominal / 66 {
        return Err(core::fmt::Error);
    }
    Ok((nominal, estimated))
}

fn capture(timer: &pac::TIM11) -> Result<u16, core::fmt::Error> {
    wait_ready(|| timer.sr().read().cc1if().bit_is_set())?;
    let value = timer.ccr1().read().ccr().bits();
    if timer.sr().read().cc1of().bit_is_set() {
        return Err(core::fmt::Error);
    }
    Ok(value)
}

fn device_uid() -> Result<String<24>, core::fmt::Error> {
    let mut uid = String::new();
    // SAFETY: RM0383 fixes the 96-bit read-only electronic signature at this address.
    let bytes = unsafe { core::slice::from_raw_parts(0x1fff7a10 as *const u8, 12) };
    for byte in bytes {
        write!(uid, "{byte:02x}")?;
    }
    Ok(uid)
}

fn identity(
    chip_id: u32,
    hz: u32,
    uid: &str,
    payload: &[u8],
    hse_hz: u32,
    hse_estimate_hz: u32,
) -> Result<String<2048>, core::fmt::Error> {
    // SAFETY: Linker bounds enclose only the immutable load image in internal Flash.
    unsafe extern "C" {
        static __flash_image_end: u8;
    }
    let flash = unsafe {
        let end = core::ptr::addr_of!(__flash_image_end) as usize;
        core::slice::from_raw_parts(0x08000000 as *const u8, end - 0x08000000)
    };
    // SAFETY: These read-only feature/control fields belong to the running core and Flash.
    let (mvfr0, ccr, acr) = unsafe {
        (
            (*cortex_m::peripheral::FPU::PTR).mvfr[0].read(),
            (*cortex_m::peripheral::SCB::PTR).ccr.read(),
            (*pac::FLASH::ptr()).acr().read().bits(),
        )
    };
    let fpscr = cortex_m::register::fpscr::read().bits();
    let mut info = String::new();
    writeln!(
        info,
        "{{\"protocol\":\"POWBENCH/1\",\"state\":\"complete\",\"run_id\":\"f411-{uid}\",\"device_id\":\"{uid}\",\"chip_id\":{chip_id},\"clock_hz\":{hz},\"hse_hz\":{hse_hz},\"hse_estimate_hz\":{hse_estimate_hz},\"fpscr\":{fpscr},\"mvfr0\":{mvfr0},\"scb_ccr\":{ccr},\"flash_acr\":{acr},\"flash_kib\":{},\"firmware_sha\":\"{}\",\"payload_sha256\":\"{}\",\"dataset_sha\":\"{}\"}}",
        stm32f4xx_hal::signature::FlashSize::get().kilo_bytes(),
        telemetry::digest(flash)?,
        telemetry::digest(payload)?,
        include_str!("../../../vectors/timing.sha256").trim()
    )?;
    Ok(info)
}
