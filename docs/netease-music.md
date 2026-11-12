**English** · [简体中文](netease-music.zh_CN.md)

# Passport Music

You need Windows 10/11, Bluetooth and the NetEase Cloud Music desktop app. No device Wi-Fi setup is needed. Online lyrics use the PC connection.

First use
1. Flash this play with the community flasher and keep Passport powered on.
2. Download [Windows control center v1.3.1](https://github.com/wyh1351/passport-music/releases/download/v1.3.1/PassportMusic-Windows-v1.3.1.zip) and extract it. Keep all programs and support folders together.
3. Open PassportMusicControl.exe and click Get Started on the home page. It installs the background bridge, creates the Passport Music desktop shortcut and enables login startup.
4. Click Open NetEase and play a song. A running player is brought back even when hidden in the tray. If remote control requires restarting NetEase, the software asks first.
5. Open Bluetooth Settings, add Passport Music and enter the six-digit code shown on the device. Pair once; the song, lyrics and progress appear after connection.

Daily use
Open the configured NetEase app. The companion runs in the background. Click the Passport Music desktop shortcut or tray icon for status. Right-click the tray for the player, reconnect, settings or exit.
Closing the window hides it in the tray. Exit stops this session; the next login follows the startup setting. Do not run a second legacy bridge alongside it.

Home controls
- UP: tap +5 volume points, double-tap +20, hold for the previous track.
- DOWN: tap -5, double-tap -20, hold for the next track.
- OK: tap play/pause, double-tap PC desktop lyrics, hold for settings.
Volume adjusts the NetEase app's own slider. Any key wakes the screen; the first gesture does not control music.

Device settings
UP/DOWN selects. Tap OK to enter or return from a detail page. Hold OK anywhere to return home.
- Top menu: Lyric Timing, Screen Settings, Appearance, Back. Back returns home.
- Screen Settings: Brightness, Screen Timeout, Back. Back returns one level.
- Appearance: Interface Background, Screen Pet, Back. Back returns one level.
Lyric timing: UP earlier, DOWN later; tap 50ms, hold 250ms, range +/-2000ms.
Brightness: 5-100%; tap 5 points, hold 20.
Timeout: 15/30 seconds, 1/2/5/10 minutes or never.
Background: Default white plus nine pixel scenes. UP/DOWN previews a name and index; the same image appears on playback and settings pages.
Pet: Headphone Cat, Dog, Rabbit, Penguin or Hidden. Pets follow playback/pause on both home and settings pages.
Changes save after about one idle second and survive restart. Settings footers stay clear.

Desktop settings
Login startup also enables recovery after an unexpected background exit. Turning it off does not interrupt the current connection. Before installation, Not Installed is a disabled indicator; start from Get Started on the home page. After installation, Reinstall Background repairs the installation.
Diagnostic Logs opens the local logs folder. Check Updates opens the download page. Lyrics are fetched online automatically; no local lyric setup is required in the UI.
During reinstallation, the button shows progress and is temporarily disabled. A completion dialog confirms that the background is running; failures show their reason. The window first opens centered on the current monitor, then remembers its size and position. It stays visible when monitors change.

Upgrading
Extract the new PC package, open its PassportMusicControl.exe and click Get Started to update the existing installation. Enable-Autostart.cmd remains available. The existing port setting, startup, pairing and files are retained. Use the desktop shortcut afterward.
For the new device menu, a compatible existing partition layout supports PassportMusic-v23-app.bin at 0x10000 without chip erase, retaining settings and pairing. FoloToy-AI-Passport-full.bin starts at 0x0 and may reset both. Never write app-only at 0x0. If unsure, use the community full flash and pair again.

Troubleshooting
- No device: keep Passport and PC Bluetooth on. Complete initial pairing; retries are automatic. Reconnect Device starts a fresh attempt.
- No internal volume/progress: reopen NetEase from the control center and follow any restart prompt.
- Lyric error: check internet access. The bridge retries; try another song. Some songs have no available online lyrics.
- Control port occupied/reserved: the default remains 9223, independent of the FlClash proxy port. Save an available port in Settings and reopen NetEase. Existing desktop/taskbar player shortcuts must use that same port; Copy Startup Arguments helps. Working installations need no port change.
- Original player shortcuts: append --remote-debugging-port=9223 --remote-debugging-address=127.0.0.1 outside the path quotes, substituting a custom port when used. Client updates or repinning may remove arguments.

Tested with NetEase 3.1.31.205174; other/future versions may need adaptation. Menus are Chinese. Chinese/Latin, Japanese kana and modern Korean are supported; other scripts and emoji may not render. Public firmware shows raw battery readings with no personal scaling. The PC package defaults to 9223 and contains no personal port file. Song content in illustrations is demonstration text; PC images are local application screenshots.
