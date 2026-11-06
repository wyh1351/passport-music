#include "music_settings.h"

static const int screen_options[]={15,30,60,120,300,600,0};
#define SCREEN_COUNT ((int)(sizeof(screen_options)/sizeof(screen_options[0])))
bool music_brightness_valid(int percent) { return percent>=5 && percent<=100 && percent%5==0; }
int music_screen_option(int seconds) {
    for (int i=0;i<SCREEN_COUNT;++i) if (screen_options[i]==seconds) return i;
    return -1;
}
bool music_screen_seconds_valid(int seconds) { return music_screen_option(seconds)>=0; }
bool music_wallpaper_valid(int wallpaper) { return wallpaper>=0 && wallpaper<MUSIC_WALLPAPER_COUNT; }
const char *music_wallpaper_name(int wallpaper) {
    static const char *names[]={"默认","蓝天小巷","霓虹夜街","夏日街角","海边小港","向日葵田","晴空老街","河畔散步","白云庭院","暮色雪港"};
    return names[music_wallpaper_valid(wallpaper)?wallpaper:0];
}
bool music_pet_valid(int pet) { return pet>=MUSIC_PET_CAT && pet<MUSIC_PET_COUNT; }
const char *music_pet_name(int pet) {
    static const char *names[]={"耳机猫","小狗","小兔","企鹅","不显示"};
    return names[music_pet_valid(pet)?pet:MUSIC_PET_CAT];
}
void music_preferences_copy(music_state_t *dest,const music_state_t *source) {
    dest->settings_page=source->settings_page; dest->settings_edit=source->settings_edit;
    dest->setting=source->setting; dest->lyric_offset_ms=source->lyric_offset_ms;
    dest->brightness=source->brightness; dest->screen_seconds=source->screen_seconds;
    dest->pet=source->pet; dest->wallpaper=source->wallpaper; dest->save_status=source->save_status;
}
unsigned music_settings_input(music_state_t *s, int key, bool held, bool twice) {
    if (!s->settings_page || key<0 || key>2) return 0;
    if ((unsigned)s->setting>=MUSIC_SETTING_COUNT) s->setting=MUSIC_SETTING_OFFSET;
    if (key==2 && twice) return 0;
    if (key==2 && held) { s->settings_page=false; s->settings_edit=false; return MUSIC_PREF_SAVE; }
    if (!s->settings_edit) {
        if (key==2) {
            s->settings_edit=true;
        } else s->setting=(s->setting+(key==0?MUSIC_SETTING_COUNT-1:1))%MUSIC_SETTING_COUNT;
        return 0;
    }
    if (key==2) { s->settings_edit=false; return MUSIC_PREF_SAVE; }
    if (s->setting==MUSIC_SETTING_WALLPAPER) {
        int previous=s->wallpaper;
        int selected=music_wallpaper_valid(previous)?previous:0;
        s->wallpaper=(selected+(key==0?MUSIC_WALLPAPER_COUNT-1:1))%MUSIC_WALLPAPER_COUNT;
        return s->wallpaper!=previous?MUSIC_PREF_CHANGED:0;
    }
    if (s->setting==MUSIC_SETTING_PET) {
        int previous=s->pet;
        int pet=music_pet_valid(previous)?previous:MUSIC_PET_CAT;
        s->pet=(music_pet_t)((pet+(key==0?MUSIC_PET_COUNT-1:1))%MUSIC_PET_COUNT);
        return (int)s->pet!=previous?MUSIC_PREF_CHANGED:0;
    }
    int *value=s->setting==MUSIC_SETTING_OFFSET?&s->lyric_offset_ms:
        s->setting==MUSIC_SETTING_SCREEN?&s->screen_seconds:&s->brightness;
    int previous=*value;
    if (s->setting==MUSIC_SETTING_OFFSET) {
        *value=music_offset_adjust(*value,key==0?1:-1,held);
    } else if (s->setting==MUSIC_SETTING_BRIGHTNESS) {
        *value+=(key==0?1:-1)*(held?20:5);
        if (*value<5) *value=5;
        if (*value>100) *value=100;
    } else {
        int index=music_screen_option(*value);
        if (index<0) index=2;
        index+=key==0?1:-1;
        if (index<0) index=0;
        if (index>=SCREEN_COUNT) index=SCREEN_COUNT-1;
        *value=screen_options[index];
    }
    return *value!=previous?MUSIC_PREF_CHANGED:0;
}

bool music_screen_input(music_screen_t *s, int64_t now, bool press, bool release, bool action) {
    if (s->suppress && !s->held && now>=s->suppress_until) s->suppress=false;
    if (press || release || action) s->activity_at=now;
    if (press) s->held=true;
    if (release) s->held=false;
    if (s->off && (press || action)) {
        s->off=false; s->suppress=true;
        s->suppress_until=now+500000;
    }
    if (s->suppress) {
        // BSP emits single/double only after its 180ms multi-click window.
        // Restart the quiet window on every part of the swallowed gesture.
        s->suppress_until=now+500000;
        return true;
    }
    return false;
}
void music_screen_tick(music_screen_t *s, int64_t now, int seconds, bool pairing) {
    if (pairing) { s->off=false; s->activity_at=now; return; }
    if (!s->off && !s->held && seconds>0 && now-s->activity_at>=(int64_t)seconds*1000000) s->off=true;
}
