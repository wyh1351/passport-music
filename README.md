[简体中文](README.zh_CN.md) · **English**

# Passport Music

Turn a pocket screen into a Bluetooth remote for NetEase Cloud Music on your Windows PC. See the current song, playback progress and three synchronized lyric lines, then use three buttons to adjust volume, change tracks, pause playback or toggle desktop lyrics.

Fine-tune lyric timing, brightness and screen timeout on the device. The companion bridge can run quietly after Windows login, ready when you open the configured player. Audio stays on your PC. Requires the Windows companion; tested with NetEase 3.1.31.205174.

[Download Windows companion and firmware](https://github.com/wyh1351/passport-music/releases/latest) · [Setup and controls](docs/netease-music.md)

## Controls

| Button | Tap | Double-tap | Hold |
| --- | --- | --- | --- |
| UP | Volume +5 | Volume +20 | Previous |
| DOWN | Volume -5 | Volume -20 | Next |
| OK | Play/pause | Desktop lyrics | Settings |

## Battery calibration scope

Battery display: after extended charging with the indicator off, the author's single device showed a raw gauge reading of 98%. The retained v13 firmware therefore includes a display calibration for that individual unit: raw 98% maps to displayed 100%, with other valid readings scaled proportionally. This observation does not establish a common AI Passport defect or a general charging fix. Other devices may show inaccurate percentages with this calibration. It does not change charging control or prove measured battery capacity is 100%. To retain raw percentages in a custom build, change MUSIC_BATTERY_FULL_SOC from 98 to 100 in main/music_battery.h and rebuild. Firmware is unchanged in this update.

## Development and validation

Based on [FoloToy/ai-passport](https://gitee.com/FoloToy/ai-passport), retaining its BSP and license. Read AGENTS.md before development. Use ESP-IDF 5.5.3 and ./tools/validate.sh; PC dependencies are in companion/requirements.txt and packaging in tools/package_music_bridge.ps1.

v1.0.1 updates the PC bridge to prefer IPv4 lyrics; firmware remains v13. Build, 61 PC regressions and C/BSP gates passed. User accepted controls, lyric timing, desktop lyrics, brightness/timeout, saved preferences and song changes with FlClash disconnected. Full0x0 flashing, a real Windows relogin, battery endurance and future client compatibility remain unverified.

Code retains upstream MIT licensing. Font/third-party terms: assets/README.md. Cover: AI-generated illustration.
