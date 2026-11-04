#pragma once
#include "music_protocol.h"

enum { MUSIC_PREF_CHANGED=1, MUSIC_PREF_SAVE=2 };
bool music_brightness_valid(int percent);
bool music_screen_seconds_valid(int seconds);
int music_screen_option(int seconds);
// Pure settings navigation. UP/DOWN/OK are 0/1/2, as in music_key_action.
unsigned music_settings_input(music_state_t *state, int key, bool held, bool twice);

typedef struct {
    int64_t activity_at, suppress_until;
    bool off, held, suppress;
} music_screen_t;
// Return true when the complete wake gesture must not control music/settings.
bool music_screen_input(music_screen_t *screen, int64_t now, bool press, bool release, bool action);
void music_screen_tick(music_screen_t *screen, int64_t now, int timeout_seconds, bool pairing);
