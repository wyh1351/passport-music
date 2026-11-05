**English** · [简体中文](netease-music.zh_CN.md)

# Passport Music

You need a Windows PC with Bluetooth and the NetEase Cloud Music desktop app. No device Wi-Fi setup is needed. Online lyrics use the PC's internet connection.

First use
1. Download PassportMusic-Windows-v1.1.1.zip from https://github.com/wyh1351/passport-music/releases/latest and extract it to a permanent folder. Keep the programs and _internal folder together.
2. Flash this play with the community flasher. For manual flashing, FoloToy-AI-Passport-full.bin starts at 0x0 and may reset old settings and bonds. Never flash an app-only upgrade at 0x0.
3. Run Enable-Autostart.cmd once for hidden operation after Windows login. Fully exit NetEase, including its tray instance, then run Open-NetEase-Remote.cmd and play a song.
4. Add a Bluetooth device in Windows Settings, choose Passport Music and enter the six-digit code shown on the device. The song, lyrics and progress appear after connection. Run only one bridge.

Home controls
- UP: tap +5 volume points, double-tap +20, hold for the previous track.
- DOWN: tap -5 volume points, double-tap -20, hold for the next track.
- OK: tap play/pause, double-tap PC desktop lyrics on/off, hold to open settings.
Volume changes the NetEase app's own slider, in percentage points.

Settings
Use UP/DOWN to select and tap OK to enter. Tap OK in a detail page to go back; hold OK anywhere in settings to return home.
- Lyric timing: UP earlier, DOWN later. Tap 50ms or hold 250ms, within +/-2000ms.
- Screen timeout: 15/30 seconds, 1/2/5/10 minutes or never.
- Brightness: 5-100%; UP brighter, DOWN dimmer. Tap 5 points or hold 20.
- Screen pet: Headphone cat, Dog, Rabbit, Penguin or Hidden. UP/DOWN cycles the choices.
Changes save after about one idle second and survive a restart. Settings footers are blank. Any key wakes the screen; that first gesture does not control the music.

Opening NetEase later
Use Open-NetEase-Remote.cmd. To use an existing desktop/taskbar shortcut, append a space and these arguments to its Target field, outside the existing path quotes:
--remote-debugging-port=9223 --remote-debugging-address=127.0.0.1
Fully exit NetEase before reopening it. For a taskbar shortcut, right-click the icon, then right-click the app name to open Properties. Client updates or repinning can remove the arguments.

Troubleshooting
- No volume/progress control: fully exit NetEase and reopen it with Open-NetEase-Remote.cmd.
- No connection: keep the device on and PC Bluetooth enabled. The bridge retries; reconnection after flashing can take time. Background-Status.cmd checks status, Stop-Background.cmd stops the bridge and Disable-Autostart.cmd disables logon startup.
- No lyrics: check internet access and try another song. You can also place a UTF-8 timed title - artist.lrc file in the bridge's lyrics folder and restart it; replace Windows-invalid filename characters with underscores.

Existing users can keep the v1.0.2/v1.0.3 companion. A compatible existing partition layout supports an app-only upgrade at 0x10000 without chip erase to retain settings. If unsure, use the community full flash and pair again.

Tested with NetEase 3.1.31.205174. Other or future versions may require adaptation. Chinese/Latin, Japanese kana and modern Korean are supported; menus remain Chinese. Other scripts and emoji may not render. Images are current-interface renders with demonstration song and lyric text.
