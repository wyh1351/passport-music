#pragma once

// Application display calibration: this device's observed charge-end gauge
// reading is 98%. BSP SOC/voltage and charger behavior remain independent.
#define MUSIC_BATTERY_FULL_SOC 98
static inline int music_battery_display_soc(int raw_soc) {
    if (raw_soc<0 || raw_soc>100) return -1;
    if (raw_soc>=MUSIC_BATTERY_FULL_SOC) return 100;
    return (raw_soc*100+MUSIC_BATTERY_FULL_SOC/2)/MUSIC_BATTERY_FULL_SOC;
}
