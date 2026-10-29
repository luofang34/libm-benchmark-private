use core::fmt::Write;

use embedded_storage::ReadStorage;
use esp_storage::FlashStorage;
use heapless::String;
use sha2::{Digest, Sha256};

const APPLICATION: u32 = 0x10000;
const MAX_IMAGE: u32 = 0x100000;

pub fn fingerprint_blocking(
    flash: &mut FlashStorage<'_>,
) -> Result<(String<64>, u32), core::fmt::Error> {
    let length = image_length_blocking(flash)?;
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 1024];
    let mut offset = 0;
    while offset < length {
        let count = (length - offset).min(buffer.len() as u32) as usize;
        flash
            .read(APPLICATION + offset, &mut buffer[..count])
            .map_err(|_| core::fmt::Error)?;
        hash.update(&buffer[..count]);
        offset += count as u32;
    }
    let mut digest = String::new();
    for byte in hash.finalize() {
        write!(digest, "{byte:02x}")?;
    }
    Ok((digest, length))
}

fn image_length_blocking(flash: &mut FlashStorage<'_>) -> Result<u32, core::fmt::Error> {
    let mut header = [0u8; 24];
    flash
        .read(APPLICATION, &mut header)
        .map_err(|_| core::fmt::Error)?;
    if header[0] != 0xe9
        || !(1..=16).contains(&header[1])
        || header[12..14] != [13, 0]
        || header[23] != 1
    {
        return Err(core::fmt::Error);
    }
    let mut offset = 24u32;
    for _ in 0..header[1] {
        let mut segment = [0u8; 8];
        flash
            .read(APPLICATION + offset, &mut segment)
            .map_err(|_| core::fmt::Error)?;
        let length = u32::from_le_bytes(segment[4..8].try_into().map_err(|_| core::fmt::Error)?);
        offset = offset
            .checked_add(8)
            .and_then(|n| n.checked_add(length))
            .ok_or(core::fmt::Error)?;
        if offset > MAX_IMAGE {
            return Err(core::fmt::Error);
        }
    }
    // The checksum occupies the last byte of a 16-byte block, followed by SHA-256.
    Ok((offset + 16) / 16 * 16 + 32)
}
