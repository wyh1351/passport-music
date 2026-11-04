#pragma once
#include "esp_err.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct { uint16_t length; uint8_t data[244]; } music_ble_chunk_t;
esp_err_t music_ble_start(void);
bool music_ble_receive(music_ble_chunk_t *chunk);
bool music_ble_send(const char *data, size_t length);
unsigned music_ble_passkey(void);
