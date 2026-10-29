// SAFETY: The ROM requires this immutable boot block at the linker-defined Flash origin.

#[unsafe(link_section = ".boot2")]
#[unsafe(no_mangle)]
#[used]
pub static BOOT2_FIRMWARE: [u8; 256] = rp2040_boot2::BOOT_LOADER_GENERIC_03H;
