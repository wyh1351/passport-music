#include "music_settings.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    assert(music_brightness_valid(5) && music_brightness_valid(75) && music_brightness_valid(100));
    assert(!music_brightness_valid(0) && !music_brightness_valid(101) && !music_brightness_valid(76));
    assert(music_screen_seconds_valid(0) && music_screen_seconds_valid(15) && music_screen_seconds_valid(600));
    assert(!music_screen_seconds_valid(-1) && !music_screen_seconds_valid(45));
    for (int pet=0;pet<MUSIC_PET_COUNT;pet++) assert(music_pet_valid(pet));
    assert(!music_pet_valid(-1) && !music_pet_valid(MUSIC_PET_COUNT));
    music_state_t pet={.settings_page=true,.settings_edit=true,.setting=MUSIC_SETTING_PET,
        .pet=MUSIC_PET_CAT,.lyric_offset_ms=350,.brightness=75,.screen_seconds=60};
    for (int i=1;i<=MUSIC_PET_COUNT;i++) {
        assert(music_settings_input(&pet,1,false,false)==MUSIC_PREF_CHANGED);
        assert((int)pet.pet==i%MUSIC_PET_COUNT);
    }
    assert(music_settings_input(&pet,0,true,false)==MUSIC_PREF_CHANGED && pet.pet==MUSIC_PET_NONE);
    assert(pet.lyric_offset_ms==350 && pet.brightness==75 && pet.screen_seconds==60);
    // Incoming song snapshots must never overwrite the user's pet or old settings.
    for (int i=0;i<120;i++) {
        music_state_t incoming={.position=i*1000,.playing=true,.pet=MUSIC_PET_CAT};
        music_preferences_copy(&incoming,&pet);
        assert(incoming.position==i*1000 && incoming.playing);
        assert(incoming.pet==MUSIC_PET_NONE && incoming.setting==MUSIC_SETTING_PET && incoming.settings_edit);
        assert(incoming.lyric_offset_ms==350 && incoming.brightness==75 && incoming.screen_seconds==60);
    }
    assert(music_settings_input(&pet,2,false,false)==MUSIC_PREF_SAVE && !pet.settings_edit && pet.settings_page);
    assert(music_settings_input(&pet,2,true,false)==MUSIC_PREF_SAVE && !pet.settings_page);
    // Top-level groups preserve selection on Back; holding OK always exits.
    music_state_t top={.settings_page=true,.lyric_offset_ms=350,.brightness=75,
        .screen_seconds=60,.pet=MUSIC_PET_PENGUIN,.wallpaper=7};
    assert(music_settings_menu_count(&top)==4);
    assert(!strcmp(music_settings_menu_name(&top,3),"返回"));
    music_settings_input(&top,0,false,false);assert(top.settings_index==3);
    music_settings_input(&top,1,false,false);assert(top.settings_index==0);
    for (int i=0;i<3;i++) music_settings_input(&top,1,false,false);
    assert(top.settings_index==3);
    assert(music_settings_input(&top,2,false,false)==MUSIC_PREF_SAVE);
    assert(!top.settings_page && !top.settings_edit && !top.settings_submenu);
    assert(top.lyric_offset_ms==350 && top.brightness==75 && top.screen_seconds==60);
    assert(top.pet==MUSIC_PET_PENGUIN && top.wallpaper==7);
    music_state_t menu={.settings_page=true,.lyric_offset_ms=350,.brightness=75,.screen_seconds=60};
    music_settings_input(&menu,1,false,false);assert(menu.settings_index==1);
    music_settings_input(&menu,2,false,false);assert(menu.settings_submenu && menu.settings_group==1);
    music_settings_input(&menu,2,false,false);assert(menu.settings_edit && menu.setting==MUSIC_SETTING_BRIGHTNESS);
    music_settings_input(&menu,2,false,false);assert(!menu.settings_edit && menu.settings_submenu);
    music_settings_input(&menu,0,false,false);assert(menu.settings_index==2);
    music_settings_input(&menu,2,false,false);assert(!menu.settings_submenu && menu.settings_index==1);
    music_settings_input(&menu,1,false,false);music_settings_input(&menu,2,false,false);
    assert(menu.settings_submenu && menu.settings_group==2);
    music_settings_input(&menu,2,false,false);assert(menu.settings_edit && menu.setting==MUSIC_SETTING_WALLPAPER);
    assert(music_settings_input(&menu,2,true,false)==MUSIC_PREF_SAVE && !menu.settings_page);
    assert(menu.lyric_offset_ms==350 && menu.brightness==75 && menu.screen_seconds==60);
    // Every detail returns without changing its value and ignores a double OK.
    for (int setting=0;setting<MUSIC_SETTING_COUNT;++setting) {
        music_state_t item={.settings_page=true,.settings_edit=true,.setting=(music_setting_t)setting,
            .settings_submenu=setting!=MUSIC_SETTING_OFFSET,.settings_group=setting>=MUSIC_SETTING_PET?2:1,
            .lyric_offset_ms=350,.brightness=75,.screen_seconds=60};
        assert(!music_settings_input(&item,2,false,true) && item.settings_edit);
        assert(music_settings_input(&item,2,false,false)==MUSIC_PREF_SAVE);
        assert(item.settings_page && !item.settings_edit);
        assert(item.lyric_offset_ms==350 && item.brightness==75 && item.screen_seconds==60);
        item.settings_edit=true;
        assert(music_settings_input(&item,2,true,false)==MUSIC_PREF_SAVE);
        assert(!item.settings_page && !item.settings_edit && !item.settings_submenu);
    }
    music_state_t s={.settings_page=true,.settings_edit=true,.setting=MUSIC_SETTING_OFFSET,
        .lyric_offset_ms=350,.brightness=75,.screen_seconds=60};
    assert(music_settings_input(&s,0,false,false)==MUSIC_PREF_CHANGED && s.lyric_offset_ms==400);
    assert(music_settings_input(&s,2,false,false)==MUSIC_PREF_SAVE && !s.settings_edit);
    s.settings_edit=true;s.setting=MUSIC_SETTING_SCREEN;
    for (int i=0;i<8;i++) music_settings_input(&s,0,false,false);
    assert(s.screen_seconds==0 && s.lyric_offset_ms==400);
    assert(music_settings_input(&s,2,false,false)==MUSIC_PREF_SAVE && s.screen_seconds==0);
    s.settings_edit=true;
    for (int i=0;i<8;i++) music_settings_input(&s,1,false,false);
    assert(s.screen_seconds==15);
    s.setting=MUSIC_SETTING_BRIGHTNESS;
    for (int i=0;i<8;i++) music_settings_input(&s,1,true,false);
    assert(s.brightness==5 && s.lyric_offset_ms==400);
    assert(!music_settings_input(&s,1,false,false));
    music_settings_input(&s,0,true,false);assert(s.brightness==25);
    for (int i=0;i<8;i++) music_settings_input(&s,0,true,false);
    assert(s.brightness==100);
    assert(music_settings_input(&s,2,true,false)==MUSIC_PREF_SAVE && !s.settings_page);
    assert(!music_settings_input(&s,0,false,false));

    // Wallpaper choice wraps in both directions and survives incoming song frames.
    assert(!music_wallpaper_valid(-1) && !music_wallpaper_valid(MUSIC_WALLPAPER_COUNT));
    music_state_t wall={.settings_page=true,.settings_edit=true,.setting=MUSIC_SETTING_WALLPAPER,
        .pet=MUSIC_PET_PENGUIN,.brightness=70,.screen_seconds=300,.lyric_offset_ms=150};
    for (int i=1;i<=MUSIC_WALLPAPER_COUNT;i++) {
        assert(music_wallpaper_valid(i-1) && music_wallpaper_name(i-1)[0]);
        assert(music_settings_input(&wall,1,false,false)==MUSIC_PREF_CHANGED);
        assert(wall.wallpaper==i%MUSIC_WALLPAPER_COUNT);
    }
    assert(music_settings_input(&wall,0,true,false)==MUSIC_PREF_CHANGED && wall.wallpaper==9);
    music_state_t fresh={.playing=true,.position=32100};music_preferences_copy(&fresh,&wall);
    assert(fresh.wallpaper==9 && fresh.pet==MUSIC_PET_PENGUIN && fresh.position==32100 && fresh.playing);
    assert(fresh.brightness==70 && fresh.screen_seconds==300 && fresh.lyric_offset_ms==150);
    assert(music_settings_input(&wall,2,false,false)==MUSIC_PREF_SAVE && !wall.settings_edit && wall.wallpaper==9);
    assert(music_settings_input(&wall,2,true,false)==MUSIC_PREF_SAVE && !wall.settings_page && wall.wallpaper==9);
    wall.settings_page=wall.settings_edit=true;wall.wallpaper=999;
    assert(music_settings_input(&wall,1,false,false)==MUSIC_PREF_CHANGED && wall.wallpaper==1);
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
