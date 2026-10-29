// SAFETY: The bootloader reads this immutable descriptor from its linker-defined section.
esp_bootloader_esp_idf::esp_app_desc!(
    env!("CARGO_PKG_VERSION"),
    env!("CARGO_PKG_NAME"),
    "unspecified",
    "unspecified",
    esp_bootloader_esp_idf::ESP_IDF_COMPATIBLE_VERSION,
    esp_bootloader_esp_idf::MMU_PAGE_SIZE,
    0,
    u16::MAX
);
