use core::fmt::Write;

use heapless::String;
use sha2::{Digest, Sha256};
use stm32f4xx_hal::otg_fs::{USB, UsbBus};
use usb_device::device::UsbDevice;
use usbd_serial::SerialPort;

pub type Port<'a> = SerialPort<'a, UsbBus<USB>>;
pub type Device<'a> = UsbDevice<'a, UsbBus<USB>>;

pub fn digest(bytes: &[u8]) -> Result<String<64>, core::fmt::Error> {
    let mut hex = String::new();
    for byte in Sha256::digest(bytes) {
        write!(hex, "{byte:02x}")?;
    }
    Ok(hex)
}

pub fn send_blocking(port: &mut Port<'_>, device: &mut Device<'_>, bytes: &[u8]) {
    let mut remaining = bytes;
    while !remaining.is_empty() {
        device.poll(&mut [port]);
        match port.write(remaining) {
            Ok(n) => remaining = &remaining[n..],
            Err(usb_device::UsbError::WouldBlock) => {}
            Err(_) => return,
        }
    }
}

pub fn serve(port: &mut Port<'_>, device: &mut Device<'_>, info: &str, payload: &[u8]) -> ! {
    let mut command = String::<64>::new();
    loop {
        device.poll(&mut [port]);
        let mut input = [0u8; 64];
        if let Ok(count) = port.read(&mut input) {
            for &byte in &input[..count] {
                if byte == b'\n' {
                    match command.trim() {
                        "POWBENCH/1 INFO" => send_blocking(port, device, info.as_bytes()),
                        "POWBENCH/1 RESULTS" => {
                            let mut header = String::<32>::new();
                            if writeln!(header, "BYTES {}", payload.len()).is_ok() {
                                send_blocking(port, device, header.as_bytes());
                                send_blocking(port, device, payload);
                            }
                        }
                        _ => {}
                    }
                    command.clear();
                } else if command.push(char::from(byte)).is_err() {
                    command.clear();
                }
            }
        }
    }
}
