#include "music_settings.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    assert(music_brightness_valid(5) && music_brightness_valid(75) && music_brightness_valid(100));
    assert(!music_brightness_valid(0) && !music_brightness_valid(101) && !music_brightness_valid(76));
    assert(music_screen_seconds_valid(0) && music_screen_seconds_valid(15) && music_screen_seconds_valid(600));
    assert(!music_screen_seconds_valid(-1) && !music_screen_seconds_valid(45));
    // Every detail uses the same return/exit rules and preserves all preferences.
    for (int setting=0;setting<MUSIC_SETTING_COUNT;++setting) {
        music_state_t item={.settings_page=true,.setting=(music_setting_t)setting,
            .lyric_offset_ms=350,.brightness=75,.screen_seconds=60};
        assert(!music_settings_input(&item,2,false,false) && item.settings_edit);
        assert(!music_settings_input(&item,2,false,true) && item.settings_edit);
        assert(music_settings_input(&item,2,false,false)==MUSIC_PREF_SAVE);
        assert(item.settings_page && !item.settings_edit);
        assert(item.lyric_offset_ms==350 && item.brightness==75 && item.screen_seconds==60);
        music_settings_input(&item,2,false,false);
        assert(music_settings_input(&item,2,true,false)==MUSIC_PREF_SAVE);
        assert(!item.settings_page && !item.settings_edit);
        assert(item.lyric_offset_ms==350 && item.brightness==75 && item.screen_seconds==60);
        item.settings_page=true;
        assert(!music_settings_input(&item,2,false,true) && item.settings_page);
        assert(music_settings_input(&item,2,true,false)==MUSIC_PREF_SAVE && !item.settings_page);
    }
    music_state_t s={.settings_page=true,.lyric_offset_ms=350,.brightness=75,.screen_seconds=60};
    assert(!music_settings_input(&s,2,false,false));
    assert(s.settings_edit && s.lyric_offset_ms==350);
    assert(music_settings_input(&s,0,false,false)==MUSIC_PREF_CHANGED && s.lyric_offset_ms==400);
    assert(music_settings_input(&s,2,false,false)==MUSIC_PREF_SAVE && !s.settings_edit);
    music_settings_input(&s,1,false,false);
    assert(s.setting==MUSIC_SETTING_SCREEN && s.lyric_offset_ms==400);
    music_settings_input(&s,2,false,false);
    for (int i=0;i<8;i++) music_settings_input(&s,0,false,false);
    assert(s.screen_seconds==0 && s.lyric_offset_ms==400);
    assert(music_settings_input(&s,2,false,false)==MUSIC_PREF_SAVE);
    assert(s.screen_seconds==0 && !s.settings_edit && s.settings_page);
    music_settings_input(&s,2,false,false);
    for (int i=0;i<8;i++) music_settings_input(&s,1,false,false);
    assert(s.screen_seconds==15);
    music_settings_input(&s,2,false,false);
    music_settings_input(&s,1,false,false);
    music_settings_input(&s,2,false,false);
    assert(s.setting==MUSIC_SETTING_BRIGHTNESS && s.settings_edit);
    for (int i=0;i<8;i++) music_settings_input(&s,1,true,false);
    assert(s.brightness==5 && s.lyric_offset_ms==400);
    assert(!music_settings_input(&s,1,false,false));
    music_settings_input(&s,0,true,false); assert(s.brightness==25);
    for (int i=0;i<8;i++) music_settings_input(&s,0,true,false);
    assert(s.brightness==100);
    assert(music_settings_input(&s,2,false,false)==MUSIC_PREF_SAVE && !s.settings_edit);
    assert(music_settings_input(&s,2,true,false)==MUSIC_PREF_SAVE && !s.settings_page);
    assert(!music_settings_input(&s,0,false,false));
    s.settings_page=true;s.setting=MUSIC_SETTING_OFFSET;s.settings_edit=true;
    assert(music_settings_input(&s,2,false,false)==MUSIC_PREF_SAVE && s.lyric_offset_ms==400);

    music_screen_t screen={0};
    music_screen_tick(&screen,14999999,15,false); assert(!screen.off);
    music_screen_tick(&screen,15000000,15,false); assert(screen.off);
    // A complete short/double/long wake gesture must never reach controls.
    assert(music_screen_input(&screen,16000000,true,false,false) && !screen.off);
    assert(music_screen_input(&screen,16100000,false,true,false));
    assert(music_screen_input(&screen,16280000,false,false,true));
    assert(!music_screen_input(&screen,17000000,true,false,false));
    assert(!music_screen_input(&screen,17100000,false,true,false));
    assert(!music_screen_input(&screen,17280000,false,false,true));
    screen.off=true;
    assert(music_screen_input(&screen,18000000,true,false,false));
    assert(music_screen_input(&screen,18500000,false,false,true));
    music_screen_tick(&screen,60000000,15,false); assert(!screen.off);
    assert(music_screen_input(&screen,61000000,false,true,false));
    assert(!music_screen_input(&screen,62000000,true,false,false));
    music_screen_input(&screen,62100000,false,true,false);
    music_screen_tick(&screen,77099999,15,false); assert(!screen.off);
    music_screen_tick(&screen,77100000,15,false); assert(screen.off);
    // Never disables automatic blanking; it does not force an asleep screen awake.
    screen=(music_screen_t){0};
    music_screen_tick(&screen,INT64_C(86400000000),0,false); assert(!screen.off);
    screen.off=true;
    music_screen_tick(&screen,INT64_C(86400000001),0,false); assert(screen.off);
    music_screen_tick(&screen,INT64_C(86400000002),15,true); assert(!screen.off);
    music_screen_tick(&screen,INT64_C(86401000000),15,true); assert(!screen.off);
    music_screen_tick(&screen,INT64_C(86415999999),15,false); assert(!screen.off);
    music_screen_tick(&screen,INT64_C(86416000000),15,false); assert(screen.off);
    puts("Music settings and screen lifecycle: PASS");
    return 0;
}
