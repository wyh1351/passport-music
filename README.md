**English** · [简体中文](README.zh_CN.md)

# Passport Music

Turn AI Passport into a wireless remote for NetEase Cloud Music on your Windows PC. See the song, progress and three synchronized lyric lines. Adjust the player's own volume, change tracks, pause playback and toggle PC desktop lyrics.

Choose from nine pixel-art backgrounds shared by playback and settings, or return to the Default white theme. Choose a headphone cat, dog, rabbit or penguin: each gently moves during playback and rests when paused. You can also hide the pet.

Adjust the background, pet, lyric timing, brightness and screen timeout on the device. Your choices survive a restart. The companion can run quietly after Windows login, ready when you open the configured player.

Requires the Windows desktop app and companion bridge. Audio plays on your PC.

<img src="docs/images/passport-music-cover.png" width="480" alt="Passport Music interface">

Current interface render with sample song and lyrics.

[Nine backgrounds](docs/images/passport-music-wallpapers.png) · [Four pets](docs/images/passport-music-pets.png) · [Controls](docs/images/passport-music-controls.png) · [Settings](docs/images/passport-music-settings.png)

## Get started

1. Flash this play with the community flasher.
2. Download and extract the Windows companion, then run `Enable-Autostart.cmd`.
3. Fully exit NetEase, then open it with `Open-NetEase-Remote.cmd`.
4. Pair **Passport Music** in Windows Bluetooth settings using the code on the device.

[Windows bridge v1.2.1](https://github.com/wyh1351/passport-music/releases/tag/bridge-v1.2.1) · [Firmware downloads](https://github.com/wyh1351/passport-music/releases/latest) · [Full instructions](docs/netease-music.md)

## Controls

| Key | Tap | Double-tap | Hold |
| --- | --- | --- | --- |
| UP | App volume +5 | +20 | Previous track |
| DOWN | App volume -5 | -20 | Next track |
| OK | Play/pause | PC desktop lyrics on/off | Settings |

Volume steps are percentage points. In settings, UP/DOWN selects, tap OK enters/returns and hold OK goes home.

## Compatibility

Requires Windows, Bluetooth and the NetEase desktop app; tested with 3.1.31.205174. Menus are Chinese. Chinese/Latin, Japanese kana and modern Korean are supported; other scripts and emoji may not render. If a client update breaks control, try reopening it with the companion launcher.

## Credits and license

Based on [FoloToy AI Passport](https://gitee.com/FoloToy/ai-passport). See [LICENSE](LICENSE) and [asset documentation](assets/README.md) for project and third-party font licensing.
