#pragma once
#include "music_protocol.h"
void music_ui_create(void);
// Pass the original BSP SOC (0..100 or -1); UI applies display calibration once.
void music_ui_update(const music_state_t *state, int battery_raw, unsigned passkey);
