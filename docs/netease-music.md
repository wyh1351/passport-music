[简体中文](netease-music.zh_CN.md) · **English**

# Passport Music

You need a Windows PC with Bluetooth, the NetEase Cloud Music desktop app, and the companion bridge. Audio plays on the PC; no device Wi-Fi setup is required. Tested with NetEase 3.1.31.205174; other or future versions may require changes.

1. Download PassportMusic-Windows-v1.0.1.zip from https://github.com/wyh1351/passport-music/releases/latest. Extract it to a permanent folder and keep PassportMusic.exe, PassportMusicBackground.exe and _internal together.
2. Flash the full firmware using the community flasher. The merged image starts at 0x0 and may reset device settings and Bluetooth bonds. Never write an app-only upgrade image at 0x0. The device initially waits for a computer.
3. Run Enable-Autostart.cmd once for hidden operation after Windows login. The bridge does not launch NetEase automatically. Fully exit NetEase, including its tray instance, then run Open-NetEase-Remote.cmd to launch the original client with remote-control arguments. Play a song.
4. In Windows Settings, add a Bluetooth device named Passport Music and enter the six-digit code shown on its screen. The device then displays the song, three lyric lines and progress. Bonded devices reconnect automatically. Run only one bridge.
5. Desktop/taskbar shortcuts also work when their target ends with --remote-debugging-port=9223 --remote-debugging-address=127.0.0.1. Fully exit the old client before relaunching. Updates or repinning may remove these arguments.

Home controls: tap UP/DOWN for +/-5 application-volume points, double-tap for +/-20, hold for previous/next track. Tap OK for play/pause, double-tap to toggle PC desktop lyrics, hold to enter settings.

Settings: UP/DOWN selects lyric timing, screen timeout or brightness; tap OK to enter. Tap OK in a detail page to return to the menu; hold OK anywhere in settings to return home. Timing changes by 50ms per tap or 250ms per hold within +/-2000ms; positive is earlier, negative later. Timeout choices are 15/30 seconds, 1/2/5/10 minutes or never. Brightness is 5-100%. Changes save automatically after about one idle second. Any key wakes the screen, consuming that first gesture.

Windows lyrics prefer IPv4 direct access, then retry with fresh proxy settings only if direct access fails. On the author's current network, exiting FlClash and changing songs passed device lyric-display and synchronization checks. Network or endpoint failures can still interrupt online lyrics. For local lyrics, put a UTF-8 timed file named title - artist.lrc in the bridge's lyrics directory and restart the bridge; replace Windows-invalid filename characters with underscores. No account cookies are read.

If progress or internal volume is unavailable, check the client arguments and fully relaunch NetEase. Background-Status.cmd checks status; Stop-Background.cmd stops the bridge, while Disable-Autostart.cmd disables logon startup. Re-pair through Windows when necessary. Temporary connection failures retry.

Battery display: after extended charging with the indicator off, the author's single device showed a raw gauge reading of 98%. The retained v13 firmware therefore includes a display calibration for that individual unit: raw 98% maps to displayed 100%, with other valid readings scaled proportionally. This observation does not establish a common AI Passport defect or a general charging fix. Other devices may show inaccurate percentages with this calibration. It does not change charging control or prove measured battery capacity is 100%. To retain raw percentages in a custom build, change MUSIC_BATTERY_FULL_SOC from 98 to 100 in main/music_battery.h and rebuild. Firmware is unchanged in this update. The cover is an illustration. The full 0x0 image passed build verification; physical feature acceptance used an app-only upgrade retaining settings. Full 0x0 flashing, an actual new Windows login and long-term battery life remain unverified.

Updating an existing bridge: run Stop-Background.cmd from the installed folder, wait for exit and back up the installation, copy the new PassportMusic folder contents over it, retain the lyrics folder, then run PassportMusicBackground.exe --background. Existing autostart need not be reinstalled. Existing v13 users only need the PC update.
