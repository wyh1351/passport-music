#pragma once
#include "music_protocol.h"

enum { MUSIC_PREF_CHANGED=1, MUSIC_PREF_SAVE=2 };
bool music_brightness_valid(int percent);
bool music_screen_seconds_valid(int seconds);
int music_screen_option(int seconds);
enum { MUSIC_WALLPAPER_COUNT=10 };
bool music_wallpaper_valid(int wallpaper);
const char *music_wallpaper_name(int wallpaper);
bool music_pet_valid(int pet);
const char *music_pet_name(int pet);
// Keep device-owned preferences when replacing the incoming music snapshot.
void music_preferences_copy(music_state_t *dest, const music_state_t *source);
// Pure settings navigation. UP/DOWN/OK are 0/1/2, as in music_key_action.
unsigned music_settings_input(music_state_t *state, int key, bool held, bool twice);
// Top menu has four rows, submenus three; negative entries are groups or Back.
int music_settings_menu_count(const music_state_t *state);
int music_settings_menu_item(const music_state_t *state, int row);
const char *music_settings_menu_name(const music_state_t *state, int row);

typedef struct {
    int64_t activity_at, suppress_until;
    bool off, held, suppress;
} music_screen_t;
// Return true when the complete wake gesture must not control music/settings.
bool music_screen_input(music_screen_t *screen, int64_t now, bool press, bool release, bool action);
void music_screen_tick(music_screen_t *screen, int64_t now, int timeout_seconds, bool pairing);
