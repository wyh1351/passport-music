#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define MUSIC_FRAME_MAX 4096
#define MUSIC_OFFSET_LIMIT_MS 2000
typedef enum { MUSIC_SAVE_OK, MUSIC_SAVE_PENDING, MUSIC_SAVE_ERROR } music_save_status_t;
typedef enum { MUSIC_SETTING_OFFSET, MUSIC_SETTING_SCREEN, MUSIC_SETTING_BRIGHTNESS, MUSIC_SETTING_PET, MUSIC_SETTING_WALLPAPER, MUSIC_SETTING_COUNT } music_setting_t;
typedef enum { MUSIC_PET_CAT, MUSIC_PET_DOG, MUSIC_PET_RABBIT, MUSIC_PET_PENGUIN, MUSIC_PET_NONE, MUSIC_PET_COUNT } music_pet_t;
typedef struct {
    char title[193], artist[193], album[193];
    char lyric[385], before[385], after[385], message[193];
    int position, duration, volume;
    int desktop_lyrics; // -1 unavailable, 0 hidden, 1 visible on the PC.
    bool connected, available, playing;
    int lyric_offset_ms, offset_ack;
    bool settings_page, settings_edit, offset_supported;
    bool settings_submenu;
    int settings_group, settings_index;
    music_setting_t setting;
    int brightness, screen_seconds;
    music_pet_t pet;
    int wallpaper; // 0: original white; 1..9: built-in static images.
    music_save_status_t save_status;
} music_state_t;
typedef struct { size_t used; bool dropping; } music_framer_t;
typedef enum { MUSIC_NONE, MUSIC_VOLUME_UP, MUSIC_VOLUME_DOWN, MUSIC_PREVIOUS,
    MUSIC_NEXT, MUSIC_TOGGLE, MUSIC_LYRIC_PREVIOUS, MUSIC_LYRIC_NEXT,
    MUSIC_DESKTOP_LYRICS, MUSIC_VOLUME_UP_20, MUSIC_VOLUME_DOWN_20,
    MUSIC_SETTINGS } music_action_t;
// key indexes match the public BSP UP/DOWN/OK enum; pure for host testing.
music_action_t music_key_action(int key, bool long_press, bool double_click);
bool music_offset_valid(int value);
int music_offset_adjust(int value, int direction, bool large_step);
const char *music_action_name(music_action_t action);
// Strict UTF-8, bounded at code point boundaries. Unsupported codepoints become '?'.
void music_text_copy(char *dst, size_t size, const char *src);
// Overlong lines are discarded until newline; next line recovers normally.
bool music_framer_feed(music_framer_t *f, uint8_t byte, char *out, size_t size);
bool music_json_flat(const char *json);
