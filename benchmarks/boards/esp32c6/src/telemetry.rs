use core::fmt::Write;

use esp_hal::{Blocking, usb_serial_jtag::UsbSerialJtag};
use heapless::String;
use sha2::{Digest, Sha256};

pub type Port<'a> = UsbSerialJtag<'a, Blocking>;

pub fn digest(bytes: &[u8]) -> Result<String<64>, core::fmt::Error> {
    let mut hex = String::new();
    for byte in Sha256::digest(bytes) {
        write!(hex, "{byte:02x}")?;
    }
    Ok(hex)
}

fn send_blocking(port: &mut Port<'_>, bytes: &[u8]) {
    port.write(bytes).ok();
    port.flush_tx().ok();
}

pub fn serve(port: &mut Port<'_>, info: &str, payload: &[u8]) -> ! {
    let mut command = String::<64>::new();
    loop {
        if let Ok(byte) = port.read_byte() {
            if byte == b'\n' {
                match command.trim() {
                    "POWBENCH/1 INFO" => send_blocking(port, info.as_bytes()),
                    "POWBENCH/1 RESULTS" => {
                        let mut header = String::<32>::new();
                        if writeln!(header, "BYTES {}", payload.len()).is_ok() {
                            send_blocking(port, header.as_bytes());
                            send_blocking(port, payload);
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
