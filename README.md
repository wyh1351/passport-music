[简体中文](README.zh_CN.md) · **English**

# Passport Music

Turn a pocket screen into a Bluetooth remote for NetEase Cloud Music on your Windows PC. See the current song, playback progress and three synchronized lyric lines, then use three buttons to adjust volume, change tracks, pause playback or toggle desktop lyrics.

Fine-tune lyric timing, brightness and screen timeout on the device. The companion bridge can run quietly after Windows login, ready when you open the configured player. Audio stays on your PC. Requires the Windows companion; tested with NetEase 3.1.31.205174.

[Download Windows companion and firmware](https://github.com/wyh1351/passport-music/releases/latest) · [Setup and controls](docs/netease-music.md)

Song text supports Chinese/existing Latin, Japanese kana and modern Korean. Menus remain Chinese; other uncovered scripts may show question marks. Install both firmware and companion for first use; existing v1.0.2 companions can be retained.

## Controls

| Button | Tap | Double-tap | Hold |
| --- | --- | --- | --- |
| UP | Volume +5 | Volume +20 | Previous |
| DOWN | Volume -5 | Volume -20 | Next |
| OK | Play/pause | Desktop lyrics | Settings |

## Battery display

Battery display: the public firmware shows the gauge percentage without scaling: raw 98% displays 98%, and 100% displays 100%. Failed or invalid readings still show “--%”. The author-specific 98%-to-100% mapping has been removed; no source edit is required to disable it. The gauge reading remains an estimate. Gauge parameters, charging control and battery capacity are unchanged.

## Development and validation

Based on [FoloToy/ai-passport](https://gitee.com/FoloToy/ai-passport), retaining its BSP and license. Read AGENTS.md before development. Use ESP-IDF 5.5.3 and ./tools/validate.sh; PC dependencies are in companion/requirements.txt and packaging in tools/package_music_bridge.ps1.

v1.0.3 / v15 public firmware displays raw battery percentages and retains Japanese/Korean text, NFC and IPv4 lyrics. Build,62 PC regressions and C/BSP gates passed. Prior controls, lyric timing, desktop lyrics, brightness/timeout, saved preferences and FlClash-disconnected song changes were user-accepted. This raw-battery public revision has host validation only and has not been flashed to the personal device. Full0x0 flashing, a real Windows relogin, battery endurance and future client compatibility remain unverified.

Code retains upstream MIT licensing. Font/third-party terms: assets/README.md. Cover: AI-generated illustration.
