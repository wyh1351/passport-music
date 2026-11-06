<p align="right">
  <a href="README.zh_CN.md">简体中文</a> · <strong>English</strong>
</p>

# Assets

This directory stores reusable fonts, images, music, sound effects, and battery profiles, organized by asset type.

Keep each asset in the matching subdirectory and document its destination, naming, integration method, and source/license. Do not mix binary assets with Markdown documentation.

## Fonts

Passport Music includes `fonts/NotoSansSC-Regular.ttf` (Google Fonts Noto Sans SC variable font, [upstream](https://github.com/google/fonts/tree/main/ofl/notosanssc), SIL OFL 1.1 in `fonts/OFL.txt`) and `fonts/NotoSansKR-Regular.ttf` ([pinned Google Fonts source](https://github.com/google/fonts/tree/4efc2774c63917927efe769ca845def6bd6debae/ofl/notosanskr), SIL OFL 1.1 in `fonts/OFL-NotoSansKR.txt`). Korean syllables/jamo use KR glyphs; existing Chinese/Latin and Japanese kana use SC glyphs. The generator preserves the existing Chinese glyphs and symbol aliases.

`tools/generate_music_font.py` (Pillow 13.0.0, fonttools 4.68.0) emits the static LVGL font, inventory and coverage header: 16 px, 2 bpp, uncompressed, 22 px line pitch; 33,664 code points, 1,123 unavailable requested points and 1,971,224 bitmap bytes. Coverage includes U+4E00-U+9FEF, ASCII/extended Latin and existing symbols, hiragana/katakana and phonetic extensions, all 11,172 modern Hangul syllables (U+AC00-U+D7A3), jamo/compatibility jamo and available half-width forms. The inventory records source/generated SHA-256, exact ranges and missing points. U+2219/U+22C5 retain their middle-dot bitmap aliases.

`main/CMakeLists.txt` compiles the const font into Flash; all music labels select it. The dependency-free coverage gate checks source hashes, actual cmap, fixed strings, Japanese and complete modern Korean coverage. Unsupported scripts/emoji/rare ideographs still become `?`. NFC normalization in the PC bridge composes canonical kana/Hangul before byte truncation; this does not claim arbitrary script shaping. See [application details](../docs/netease-music.md).

Store reusable font files and generated font sources in `fonts/`.

- Use descriptive names that include the family, weight, size, and format when relevant.
- Document the source, license, character range, conversion command, and expected destination.
- Check Flash and internal-RAM impact before adding a font; the ESP32-C3 has no PSRAM.
- Do not commit fonts whose license does not permit redistribution.

## Images

Store reusable source images and generated display assets in `images/`.

| File | Dimensions and format | Use and source |
| --- | --- | --- |
| [`images/home.jpg`](images/home.jpg) | 3840 × 2160, JPEG | Product hero image embedded in both project README files to foreground AI Passport and its open, maker-oriented identity. |
| [`images/readme-hardware-specs.png`](images/readme-hardware-specs.png) | 2172 × 724, PNG RGBA | Optional technical infographic retained as a reference asset; it is no longer used as the homepage hero. Generated for this repository with the built-in image generation tool on 2026-09-17; the six labels and values were checked against the documented hardware contract. |
| [`images/logo-wordmark.png`](images/logo-wordmark.png) | 1648 × 336, PNG RGBA | Transparent black wordmark extracted from the repository's original `images/logo.png`; embedded in both project README files for light backgrounds. |
| [`images/logo-wordmark-dark.png`](images/logo-wordmark-dark.png) | 1648 × 336, PNG RGBA | White version of the extracted wordmark, used by the README `<picture>` element when GitHub is in dark mode. |

- Use descriptive names and document dimensions, pixel format, conversion steps, and destination.
- Prefer formats suitable for the 240 × 320 ARGB8888 display and account for Flash and internal RAM.
- Preserve editable sources where licensing permits, and record the source and license.
- Never commit device QR secrets, credentials, or personal data in images.

## Music and sound effects

Store reusable music and sound-effect sources in `music/`.

- Document the source, license, sample rate, bit depth, channels, conversion command, and destination.
- Prefer 16 kHz, 16-bit mono PCM when it matches the current BSP audio path.
- Check Flash and internal-RAM cost before embedding audio; stream or chunk long recordings.
- Do not commit media without redistribution permission.

## Battery profiles

[`battery/wanli-500mah-profile2-xil40x-20261020.txt`](battery/wanli-500mah-profile2-xil40x-20261020.txt)
contains the supplied CW2017 profile for the Wanli New Energy 500 mAh cell
(profile2, XIL40X, 2026-10-20). It is an unchanged copy of the project-supplied
file, retained at the maintainer's request for this firmware update. Its
original filename is recorded in the paired Chinese document. No separate
license was included in the supplied file.

The format is 80 lines of two hexadecimal digits, one byte per line in register
order. The BSP embeds those bytes in `components/bsp/src/bsp_battery.c`; the
host gate checks the source file and initializer for an exact match. Text-file
SHA-256: `7ea96eba4634f4495a37c25ffacd54c1deaa0693b162c892d671a2ba68460919`.
Decoded 80-byte SHA-256:
`fa7365671093ef449c5bdcfb4adb279e3d275f888109f50b6b2f21e9b96220d5`.
This is a fuel-gauge profile, not a charging configuration or a generic profile
for every 500 mAh cell; see the [hardware guide](../docs/hardware-design/AI_HARDWARE_DEVELOPMENT_GUIDE.md#9-cw2017-fuel-gauge).


## Passport Music cover

`images/passport-music-cover.png` is an AI-generated play illustration, not a device photograph or runtime screenshot. Generated with the built-in image tool for this release; no third-party photos or song lyrics are included.

## A1 interface assets

Original code-drawn pixel-cat artwork: `images/music-cat-play.svg` and
`images/music-cat-rest.svg`, under the repository MIT license. Regenerate the
two40x40 ARGB8888 frames in `images/music_cat.c` with
`python tools/generate_music_cat.py` (Pillow13.0.0).
`python tools/generate_music_font.py --size 20` for `fonts/music_font_20.c`
and `fonts/music_font_20_inventory.json`. The20px font shares the same licensed
SC/KR sources and exact coverage as16px. Gate hashes validate both sizes.

## Additional original pets

`images/music-dog-*.svg`, `images/music-rabbit-*.svg` and
`images/music-penguin-*.svg` are original integer-grid artwork under the
repository MIT license. The existing `generate_music_cat.py` emits all four
animals' play/rest frames into `images/music_cat.c`: eight40x40 ARGB8888 frames,
51200 bytes total. All animations use the same pose function and position.

## Release interface images

`../docs/images/passport-music-*.png` compose this application's native interface renders and original pixel pets. Song/lyrics are sample content, not live telemetry or device photographs. Settings footers are intentionally blank; new footer hints or status text require the creator's explicit approval.

## Selectable static wallpapers

`images/wallpapers/01.jpg` through `09.jpg` are nine pixel-art images supplied by the creator. Original authors and licenses were not provided; these are not original MIT artwork. The submitting creator supplied these images and requested their inclusion in this public release. Original creators retain their rights; no MIT license grant is claimed for these backgrounds. Run `python tools/generate_music_wallpapers.py` (Pillow13.0.0) for aspect-preserving scaling, bottom cropping and `images/music_wallpapers.c`. Each is240x320 I8; all nine use700416 bytes. LVGL decodes one row at a time; full-frame RAM loading is forbidden. Settings support the original white background plus all nine images and persist the choice in NVS.
