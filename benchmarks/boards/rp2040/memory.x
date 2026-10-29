MEMORY {
    BOOT2 : ORIGIN = 0x10000000, LENGTH = 0x100
    /* A bounded image window, not a claim about the unqueried Flash capacity. */
    FLASH : ORIGIN = 0x10000100, LENGTH = 128K - 0x100
    RAM : ORIGIN = 0x20000000, LENGTH = 256K
}

EXTERN(BOOT2_FIRMWARE)
SECTIONS {
    .boot2 ORIGIN(BOOT2) : { KEEP(*(.boot2)); } > BOOT2
} INSERT BEFORE .text;

__flash_image_end = MAX(ADDR(.rodata) + SIZEOF(.rodata), LOADADDR(.data) + SIZEOF(.data));
