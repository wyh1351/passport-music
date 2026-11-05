#pragma once

// Public firmware shows the gauge percentage without per-device scaling.
// Keep invalid/unavailable readings distinct from an empty battery.
static inline int music_battery_display_soc(int raw_soc) {
    if (raw_soc<0 || raw_soc>100) return -1;
    return raw_soc;
}
