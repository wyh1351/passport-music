#include "music_ui.h"
#include "music_settings.h"
#include "music_battery.h"
#include "music_cat.h"
#include "music_wallpapers.h"
#include "lvgl.h"
#include <stdio.h>
#include <string.h>
LV_FONT_DECLARE(music_font_16);
LV_FONT_DECLARE(music_font_20);
LV_IMAGE_DECLARE(music_cat_play);
LV_IMAGE_DECLARE(music_cat_rest);
LV_IMAGE_DECLARE(music_dog_play);
LV_IMAGE_DECLARE(music_dog_rest);
LV_IMAGE_DECLARE(music_rabbit_play);
LV_IMAGE_DECLARE(music_rabbit_rest);
LV_IMAGE_DECLARE(music_penguin_play);
LV_IMAGE_DECLARE(music_penguin_rest);
enum { INK=0x191b1f, MUTED=0x616876, RULE=0xdfe2e7, RED=0xe4002b, SOFT=0xfff0f3 };
static lv_obj_t *background;
static lv_obj_t *shadow_source[8],*shadow_label[8];
static int background_id=-1,theme_id=-1;
static lv_obj_t *status,*battery_label,*title,*artist,*before,*current,*after;
static lv_obj_t *progress,*elapsed,*duration,*volume,*desktop,*divider,*accent,*cat;
static lv_obj_t *rows[MUSIC_SETTING_COUNT],*names[MUSIC_SETTING_COUNT],*values[MUSIC_SETTING_COUNT],*detail_hint;
static lv_obj_t *label(lv_obj_t *root,int x,int y,int w,int h,uint32_t color,const lv_font_t *font) {
    lv_obj_t *o=lv_label_create(root); lv_obj_remove_style_all(o);
    lv_obj_set_pos(o,x,y); lv_obj_set_size(o,w,h);
    lv_obj_set_style_text_font(o,font,0); lv_obj_set_style_text_color(o,lv_color_hex(color),0);
    lv_label_set_long_mode(o,LV_LABEL_LONG_DOT); return o;
}
static lv_obj_t *box(lv_obj_t *root,int x,int y,int w,int h,uint32_t color) {
    lv_obj_t *o=lv_obj_create(root); lv_obj_remove_style_all(o);
    lv_obj_set_pos(o,x,y); lv_obj_set_size(o,w,h);
    lv_obj_set_style_bg_color(o,lv_color_hex(color),0); lv_obj_set_style_bg_opa(o,LV_OPA_COVER,0);
    lv_obj_remove_flag(o,LV_OBJ_FLAG_SCROLLABLE); return o;
}
static void show(lv_obj_t *o,bool visible) {
    if (visible) lv_obj_remove_flag(o,LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(o,LV_OBJ_FLAG_HIDDEN);
}
static void text(lv_obj_t *o,const char *value) {
    if (strcmp(lv_label_get_text(o),value)) lv_label_set_text(o,value);
}
static void timeout_text(char *out,size_t size,int seconds) {
    if (!seconds) snprintf(out,size,"永不息屏");
    else if (seconds<60) snprintf(out,size,"%d 秒",seconds);
    else snprintf(out,size,"%d 分钟",seconds/60);
}
static void pet_update(const music_state_t *s) {
    static const lv_image_dsc_t *sprites[MUSIC_PET_NONE][2]={
        {&music_cat_play,&music_cat_rest},{&music_dog_play,&music_dog_rest},
        {&music_rabbit_play,&music_rabbit_rest},{&music_penguin_play,&music_penguin_rest}};
    int selected=music_pet_valid(s->pet)?s->pet:MUSIC_PET_CAT;
    show(cat,selected!=MUSIC_PET_NONE);
    if (selected==MUSIC_PET_NONE) return;
    bool playing=s->connected && s->available && s->playing && !s->settings_page;
    music_cat_pose_t pose=music_cat_pose(lv_tick_get(),playing);
    const lv_image_dsc_t *src=sprites[selected][pose.closed?1:0];
    if (lv_image_get_src(cat)!=src) lv_image_set_src(cat,src);
    lv_obj_set_y(cat,46+pose.dy);
}
void music_ui_create(void) {
    lv_obj_t *root=lv_obj_create(NULL); lv_obj_remove_style_all(root);
    lv_obj_set_style_bg_color(root,lv_color_hex(0xffffff),0); lv_obj_set_style_bg_opa(root,LV_OPA_COVER,0);
    lv_obj_set_style_text_font(root,&music_font_16,0); lv_obj_remove_flag(root,LV_OBJ_FLAG_SCROLLABLE);
    background=lv_image_create(root); lv_obj_set_pos(background,0,0); show(background,false);
    status=label(root,16,12,151,24,RED,&music_font_16);
    battery_label=label(root,174,16,50,20,MUTED,&lv_font_montserrat_14);
    lv_obj_set_style_text_align(battery_label,LV_TEXT_ALIGN_RIGHT,0);
    title=label(root,16,47,166,29,INK,&music_font_20);
    lv_label_set_long_mode(title,LV_LABEL_LONG_SCROLL_CIRCULAR);
    lv_obj_set_style_anim_duration(title,7000,0);
    artist=label(root,16,83,208,24,MUTED,&music_font_16);
    cat=lv_image_create(root); lv_obj_set_pos(cat,190,46); lv_image_set_src(cat,&music_cat_rest);
    divider=box(root,16,111,208,1,RULE);
    before=label(root,16,128,208,24,MUTED,&music_font_16);
    accent=box(root,16,163,3,58,RED);
    current=label(root,27,162,197,58,RED,&music_font_20);
    lv_obj_set_style_text_line_space(current,1,0);
    after=label(root,16,233,208,24,MUTED,&music_font_16);
    progress=lv_bar_create(root); lv_obj_remove_style_all(progress);
    lv_obj_set_pos(progress,16,266); lv_obj_set_size(progress,208,3);
    lv_obj_set_style_bg_opa(progress,LV_OPA_COVER,LV_PART_MAIN);
    lv_obj_set_style_bg_color(progress,lv_color_hex(RULE),LV_PART_MAIN);
    lv_obj_set_style_bg_opa(progress,LV_OPA_COVER,LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(progress,lv_color_hex(RED),LV_PART_INDICATOR); lv_bar_set_range(progress,0,1000);
    elapsed=label(root,16,274,106,20,MUTED,&lv_font_montserrat_14);
    duration=label(root,130,274,94,20,MUTED,&lv_font_montserrat_14);
    lv_obj_set_style_text_align(duration,LV_TEXT_ALIGN_RIGHT,0);
    volume=label(root,16,296,103,24,INK,&music_font_16);
    desktop=label(root,119,296,105,24,MUTED,&music_font_16);
    lv_obj_set_style_text_align(desktop,LV_TEXT_ALIGN_RIGHT,0);
    for (int i=0;i<MUSIC_SETTING_COUNT;i++) {
        rows[i]=box(root,12,112+i*33,216,32,0xffffff);
        names[i]=label(rows[i],10,3,106,24,INK,&music_font_16);
        values[i]=label(rows[i],116,5,90,24,MUTED,&lv_font_montserrat_14);
        lv_obj_set_style_text_align(values[i],LV_TEXT_ALIGN_RIGHT,0);
        if (i==MUSIC_SETTING_SCREEN || i==MUSIC_SETTING_PET || i==MUSIC_SETTING_WALLPAPER) lv_obj_set_style_text_font(values[i],&music_font_16,0);
    }
    detail_hint=label(root,16,126,208,26,MUTED,&music_font_16);
    lv_obj_t *sources[]={before,current,after,elapsed,duration,volume,desktop,detail_hint};
    for (unsigned i=0;i<8;i++) {
        shadow_source[i]=sources[i];
        shadow_label[i]=label(root,0,0,1,1,0x111b32,lv_obj_get_style_text_font(sources[i],0));
        lv_obj_set_style_text_opa(shadow_label[i],230,0);
        lv_obj_move_to_index(shadow_label[i],lv_obj_get_index(sources[i]));
        show(shadow_label[i],false);
    }
    music_state_t initial={.desktop_lyrics=-1}; music_ui_update(&initial,-1,1000000); lv_screen_load(root);
}
static void music_ui_update_content(const music_state_t *s,int battery_raw,unsigned passkey) {
    char b[112]; int battery=music_battery_display_soc(battery_raw);
    if (battery<0) snprintf(b,sizeof(b),"--%%"); else snprintf(b,sizeof(b),"%d%%",battery);
    text(battery_label,b); pet_update(s);
    bool menu=s->settings_page && !s->settings_edit,detail=s->settings_page && s->settings_edit;
    for (int i=0;i<MUSIC_SETTING_COUNT;i++) show(rows[i],menu);
    show(detail_hint,detail);
    show(before,!s->settings_page); show(after,!s->settings_page); show(current,!menu); show(accent,!s->settings_page);
    show(progress,!menu && !(detail && (s->setting==MUSIC_SETTING_PET || s->setting==MUSIC_SETTING_WALLPAPER))); show(elapsed,!s->settings_page); show(duration,!s->settings_page);
    show(volume,!s->settings_page); show(desktop,!s->settings_page);
    lv_obj_set_style_text_align(current,detail?LV_TEXT_ALIGN_CENTER:LV_TEXT_ALIGN_LEFT,0);
    lv_obj_set_pos(current,detail?16:27,detail?174:162); lv_obj_set_width(current,detail?208:197);
    if (s->settings_page) {
        text(status,"设备设置");
        if (menu) {
            text(title,"显示与歌词"); text(artist,"歌词、显示与宠物");
            const char *items[]={"歌词微调","自动息屏","屏幕亮度","屏幕宠物","界面背景"};
            bool painted=music_wallpaper_valid(s->wallpaper) && s->wallpaper!=0;
            for (int i=0;i<MUSIC_SETTING_COUNT;i++) {
                bool selected=(int)s->setting==i;
                lv_obj_set_style_bg_color(rows[i],lv_color_hex(painted?0x111b32:selected?SOFT:0xffffff),0);
                lv_obj_set_style_bg_opa(rows[i],painted?(selected?150:76):LV_OPA_COVER,0);
                lv_obj_set_style_border_color(rows[i],lv_color_hex(selected?(painted?0xffe7a0:RED):(painted?0xffffff:RULE)),0);
                lv_obj_set_style_border_opa(rows[i],painted && !selected?70:LV_OPA_COVER,0);
                lv_obj_set_style_border_width(rows[i],selected?3:1,0);
                lv_obj_set_style_border_side(rows[i],selected?LV_BORDER_SIDE_LEFT:LV_BORDER_SIDE_BOTTOM,0);
                lv_obj_set_style_text_color(names[i],lv_color_hex(selected?(painted?0xffe7a0:RED):(painted?0xeaf1ff:INK)),0);
                lv_obj_set_style_text_color(values[i],lv_color_hex(selected?(painted?0xffe7a0:RED):(painted?0xeaf1ff:MUTED)),0); text(names[i],items[i]);
            }
            snprintf(b,sizeof(b),"%+d ms",s->lyric_offset_ms); text(values[0],b);
            timeout_text(b,sizeof(b),s->screen_seconds); text(values[1],b);
            snprintf(b,sizeof(b),"%d%%",s->brightness); text(values[2],b);
            text(values[MUSIC_SETTING_PET],music_pet_name(s->pet));
            text(values[MUSIC_SETTING_WALLPAPER],music_wallpaper_name(s->wallpaper));
            if (!s->connected && passkey<1000000) { snprintf(b,sizeof(b),"配对码：%06u",passkey); text(artist,b); }
            return;
        }
        if (s->setting==MUSIC_SETTING_OFFSET) {
            text(title,"歌词对齐微调"); text(artist,"正值更早 / 负值更晚"); text(detail_hint,"短按 50ms / 长按 250ms");
            snprintf(b,sizeof(b),"%+d ms",s->lyric_offset_ms); text(current,b);
            lv_bar_set_value(progress,(s->lyric_offset_ms+MUSIC_OFFSET_LIMIT_MS)*1000/(2*MUSIC_OFFSET_LIMIT_MS),LV_ANIM_OFF);
        } else if (s->setting==MUSIC_SETTING_SCREEN) {
            text(title,"自动息屏"); text(artist,"无按键操作后关闭背光"); text(detail_hint,"播放音乐时同样生效");
            timeout_text(b,sizeof(b),s->screen_seconds); text(current,b);
            lv_bar_set_value(progress,music_screen_option(s->screen_seconds)*1000/6,LV_ANIM_OFF);
        } else if (s->setting==MUSIC_SETTING_WALLPAPER) {
            text(title,"界面背景"); text(artist,music_wallpaper_name(s->wallpaper));
            text(detail_hint,""); text(current,"");
        } else if (s->setting==MUSIC_SETTING_PET) {
            text(title,"屏幕宠物"); text(artist,"歌名旁的像素小伙伴");
            text(detail_hint,"上 / 下选择，自动保存"); text(current,music_pet_name(s->pet));
        } else {
            text(title,"屏幕亮度"); text(artist,"立即预览 / 自动保存"); text(detail_hint,"短按 5% / 长按 20%");
            snprintf(b,sizeof(b),"%d %%",s->brightness); text(current,b); lv_bar_set_value(progress,s->brightness*10,LV_ANIM_OFF);
        }
        if (!s->connected && passkey<1000000) { snprintf(b,sizeof(b),"配对码：%06u",passkey); text(artist,b); }
        return;
    }
    text(status,!s->connected?"等待电脑连接":!s->available?"网易云未就绪":s->playing?"正在播放":"已暂停");
    text(title,s->connected && s->title[0]?s->title:"随身音乐遥控器"); text(artist,s->connected?s->artist:"Passport Music / 蓝牙");
    text(before,s->connected?s->before:"");
    if (!s->connected && passkey<1000000) { snprintf(b,sizeof(b),"配对码：%06u",passkey); text(current,b); }
    else text(current,!s->connected?(passkey==1000001?"蓝牙启动失败\n请使用 USB":"等待电脑\n音乐桥接连接"):s->lyric[0]?s->lyric:s->message);
    text(after,s->connected?s->after:"");
    lv_bar_set_value(progress,s->connected && s->duration>0?(int)((int64_t)s->position*1000/s->duration):0,LV_ANIM_OFF);
    if (s->connected && s->duration>0) {
        snprintf(b,sizeof(b),"%02d:%02d",s->position/60000,s->position/1000%60); text(elapsed,b);
        snprintf(b,sizeof(b),"%02d:%02d",s->duration/60000,s->duration/1000%60); text(duration,b);
    } else { text(elapsed,s->connected?"--:--":""); text(duration,""); }
    if (s->connected) {
        if (s->volume<0) snprintf(b,sizeof(b),"音量 --"); else snprintf(b,sizeof(b),"音量 %d%%",s->volume);
        text(volume,b); text(desktop,s->desktop_lyrics<0?"":s->desktop_lyrics?"桌面歌词 开":"桌面歌词 关");
    } else { text(volume,""); text(desktop,""); }
}

// The selected static Flash background is shared by home and all settings pages.
void music_ui_update(const music_state_t *s,int battery_raw,unsigned passkey) {
    music_ui_update_content(s,battery_raw,passkey);
    int id=music_wallpaper_valid(s->wallpaper)?s->wallpaper:0;
    bool painted=id!=0;
    if (id!=background_id) {
        show(background,painted);
        if (painted) lv_image_set_src(background,music_wallpaper_image(id));
        background_id=id;
    }
    if ((int)painted!=theme_id) {
        lv_obj_t *items[]={status,battery_label,title,artist,before,current,after,elapsed,duration,volume,desktop,detail_hint};
        const uint32_t plain[]={RED,MUTED,INK,MUTED,MUTED,RED,MUTED,MUTED,MUTED,INK,MUTED,MUTED};
        for (unsigned i=0;i<sizeof(items)/sizeof(items[0]);i++) {
            uint32_t color=painted?(items[i]==current?0xffe7a0:items[i]==title?0xffffff:0xeaf1ff):plain[i];
            lv_obj_set_style_text_color(items[i],lv_color_hex(color),0);
        }
        lv_obj_set_style_bg_color(accent,lv_color_hex(painted?0xffe7a0:RED),0);
        lv_obj_set_style_bg_color(divider,lv_color_hex(painted?0xffffff:RULE),0);
        lv_obj_set_style_bg_opa(divider,painted?80:LV_OPA_COVER,0);
        lv_obj_set_style_bg_color(progress,lv_color_hex(painted?0x29384c:RULE),LV_PART_MAIN);
        lv_obj_set_style_bg_color(progress,lv_color_hex(painted?0xffe7a0:RED),LV_PART_INDICATOR);
        theme_id=painted;
    }
    for (unsigned i=0;i<8;i++) {
        lv_obj_t *src=shadow_source[i],*dst=shadow_label[i];
        bool visible=painted && !lv_obj_has_flag(src,LV_OBJ_FLAG_HIDDEN);
        show(dst,visible);
        if (!visible) continue;
        lv_obj_set_pos(dst,lv_obj_get_x(src)+1,lv_obj_get_y(src)+1);
        int height=lv_obj_get_height(src);
        if (lv_obj_get_y(src)+1+height>320) height=320-lv_obj_get_y(src)-1;
        lv_obj_set_size(dst,lv_obj_get_width(src),height);
        lv_obj_set_style_text_align(dst,lv_obj_get_style_text_align(src,0),0);
        lv_obj_set_style_text_line_space(dst,lv_obj_get_style_text_line_space(src,0),0);
        text(dst,lv_label_get_text(src));
    }
}
