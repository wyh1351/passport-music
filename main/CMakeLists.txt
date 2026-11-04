idf_component_register(
    SRCS "main.c" "music_protocol.c" "music_ui.c" "music_ble.c" "music_settings.c" "../assets/fonts/music_font_16.c"
    INCLUDE_DIRS "."
    REQUIRES bsp bt nvs_flash esp_timer esp_driver_usb_serial_jtag json
)
