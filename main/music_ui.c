#include "music_ui.h"
#include "music_settings.h"
#include "music_battery.h"
#include "lvgl.h"
#include <stdio.h>
#include <string.h>
LV_FONT_DECLARE(music_font_16);
static lv_obj_t *status, *battery_label, *title, *artist, *album, *line1, *line2, *line3, *footer, *progress, *volume;
static lv_obj_t *label(lv_obj_t *root, int x, int y, int w, int h, uint32_t color) {
    lv_obj_t *o = lv_label_create(root);
    lv_obj_set_pos(o, x, y); lv_obj_set_size(o, w, h);
    lv_obj_set_style_text_font(o, &music_font_16, 0);
    lv_obj_set_style_text_color(o, lv_color_hex(color), 0);
    lv_label_set_long_mode(o, LV_LABEL_LONG_DOT);
    return o;
}
static void text(lv_obj_t *o, const char *value) {
    if (strcmp(lv_label_get_text(o), value)) lv_label_set_text(o, value);
}
static void timeout_text(char *out, size_t size, int seconds) {
    if (!seconds) snprintf(out,size,"永不息屏");
    else if (seconds<60) snprintf(out,size,"%d 秒",seconds);
    else snprintf(out,size,"%d 分钟",seconds/60);
}
void music_ui_create(void) {
    lv_obj_t *root = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(root, lv_color_hex(0x101318), 0);
    lv_obj_set_style_text_font(root, &music_font_16, 0);
    lv_obj_remove_flag(root, LV_OBJ_FLAG_SCROLLABLE);
    status = label(root, 22, 14, 144, 22, 0xef6b65);
    battery_label = label(root, 178, 14, 42, 22, 0xa4adb8);
    title = label(root, 18, 50, 204, 48, 0xffffff);
    lv_label_set_long_mode(title, LV_LABEL_LONG_WRAP);
    artist = label(root, 18, 102, 204, 23, 0xb0bac8);
    album = label(root, 18, 129, 204, 23, 0x798798);
    line1 = label(root, 18, 163, 204, 24, 0x798798);
    line2 = label(root, 18, 189, 204, 46, 0xffd8a8);
    lv_label_set_long_mode(line2, LV_LABEL_LONG_WRAP);
    line3 = label(root, 18, 237, 204, 23, 0x798798);
    progress = lv_bar_create(root);
    lv_obj_set_pos(progress, 18, 267); lv_obj_set_size(progress, 204, 4);
    lv_obj_set_style_bg_color(progress, lv_color_hex(0x303742), LV_PART_MAIN);
    lv_obj_set_style_bg_color(progress, lv_color_hex(0xef6b65), LV_PART_INDICATOR);
    lv_bar_set_range(progress, 0, 1000);
    volume = label(root, 18, 276, 204, 21, 0xc9d2dc);
    footer = label(root, 18, 298, 204, 20, 0x798798);
    music_state_t initial = {.desktop_lyrics=-1}; music_ui_update(&initial, -1, 1000000);
    lv_screen_load(root);
}
void music_ui_update(const music_state_t *s, int battery_raw, unsigned passkey) {
    int battery=music_battery_display_soc(battery_raw);
    char b[96];
    if (battery < 0) snprintf(b, sizeof(b), "--%%");
    else snprintf(b, sizeof(b), "%d%%", battery);
    text(battery_label, b);
    lv_obj_set_style_text_align(line2,s->settings_page && s->settings_edit?LV_TEXT_ALIGN_CENTER:LV_TEXT_ALIGN_LEFT,0);
    lv_obj_remove_flag(line3,LV_OBJ_FLAG_HIDDEN); lv_obj_remove_flag(progress,LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_y(artist,102); lv_obj_set_y(album,129); lv_obj_set_y(line1,163); lv_obj_set_y(line2,189);
    lv_obj_set_style_text_color(artist,lv_color_hex(0xb0bac8),0);
    lv_obj_set_style_text_color(album,lv_color_hex(0x798798),0);
    lv_obj_set_style_text_color(line1,lv_color_hex(0x798798),0);
    lv_obj_set_style_text_color(line2,lv_color_hex(0xffd8a8),0);
    if (s->settings_page) {
        if (!s->settings_edit) {
            text(status,"设备设置"); text(title,"显示与歌词");
            lv_obj_set_y(artist,108); lv_obj_set_y(album,148); lv_obj_set_y(line1,188); lv_obj_set_y(line2,225);
            lv_obj_add_flag(line3,LV_OBJ_FLAG_HIDDEN); lv_obj_add_flag(progress,LV_OBJ_FLAG_HIDDEN);
            snprintf(b,sizeof(b),"%s歌词微调  %+dms",s->setting==MUSIC_SETTING_OFFSET?"> ":"  ",s->lyric_offset_ms); text(artist,b);
            char duration[32]; timeout_text(duration,sizeof(duration),s->screen_seconds);
            snprintf(b,sizeof(b),"%s自动息屏  %s",s->setting==MUSIC_SETTING_SCREEN?"> ":"  ",duration); text(album,b);
            snprintf(b,sizeof(b),"%s屏幕亮度  %d%%",s->setting==MUSIC_SETTING_BRIGHTNESS?"> ":"  ",s->brightness); text(line1,b);
            lv_obj_t *selected=s->setting==MUSIC_SETTING_OFFSET?artist:s->setting==MUSIC_SETTING_SCREEN?album:line1;
            lv_obj_set_style_text_color(selected,lv_color_hex(0xffd8a8),0);
            if (!s->connected && passkey<1000000) { snprintf(b,sizeof(b),"蓝牙配对码：%06u",passkey); text(line2,b); }
            else text(line2,s->setting==MUSIC_SETTING_OFFSET?"调整歌词提前或延后":s->setting==MUSIC_SETTING_SCREEN?"设置自动息屏时长":"调节亮屏时的背光");
            text(volume,""); text(footer,"");
            return;
        }
        if (s->setting!=MUSIC_SETTING_OFFSET) {
            bool screen=s->setting==MUSIC_SETTING_SCREEN;
            text(status,"显示设置"); text(title,screen?"自动息屏":"屏幕亮度");
            text(artist,screen?"无按键操作后关闭背光":"上键增亮 / 下键调暗");
            if (!s->connected && passkey<1000000) { snprintf(b,sizeof(b),"蓝牙配对码：%06u",passkey); text(album,b); }
            else text(album,screen?"播放音乐时同样生效":"立即预览 / 自动保存");
            text(line1,screen?"上键延长 / 下键缩短":"短按 5%  长按 20%");
            if (screen) timeout_text(b,sizeof(b),s->screen_seconds);
            else snprintf(b,sizeof(b),"%d %%",s->brightness);
            text(line2,b);
            text(line3,s->save_status==MUSIC_SAVE_PENDING?"正在保存":s->save_status==MUSIC_SAVE_ERROR?"保存失败，仅本次有效":"已保存");
            lv_bar_set_value(progress,screen?music_screen_option(s->screen_seconds)*1000/6:s->brightness*10,LV_ANIM_OFF);
            text(volume,screen?"":"范围 5% 至 100%");
            text(footer,"");
            return;
        }
        text(status,"对齐设置"); text(title,"歌词对齐微调");
        text(artist,"上键提前 / 下键延后");
        if (!s->connected && passkey<1000000) {
            snprintf(b,sizeof(b),"蓝牙配对码：%06u",passkey); text(album,b);
        } else text(album,"正值更早 / 负值更晚");
        text(line1,"短按 50ms  长按 250ms");
        snprintf(b,sizeof(b),"%+d ms",s->lyric_offset_ms); text(line2,b);
        text(line3,s->save_status==MUSIC_SAVE_PENDING?"正在保存":s->save_status==MUSIC_SAVE_ERROR?"保存失败，仅本次有效":
            !s->connected?"已保存 / 等待连接":!s->offset_supported?"请更新电脑桥接":
            s->offset_ack!=s->lyric_offset_ms?"已保存 / 等待同步":"已保存 / 已同步");
        lv_bar_set_value(progress,(s->lyric_offset_ms+MUSIC_OFFSET_LIMIT_MS)*1000/(2*MUSIC_OFFSET_LIMIT_MS),LV_ANIM_OFF);
        text(volume,"范围 -2000 至 +2000ms");
        text(footer,"");
        return;
    }
    text(status, !s->connected ? "等待电脑连接" : !s->available ? "网易云未就绪" : s->playing ? "正在播放" : "已暂停");
    text(title, s->connected && s->title[0] ? s->title : "随身音乐遥控器");
    text(artist, s->connected ? s->artist : "蓝牙名称：Passport Music");
    text(album, s->connected ? s->album : "电脑网易云音乐遥控");
    text(line1, s->connected ? s->before : "");
    if (!s->connected && passkey < 1000000) {
        snprintf(b, sizeof(b), "蓝牙配对码：%06u", passkey); text(line2, b);
    } else text(line2, !s->connected ? (passkey==1000001 ? "蓝牙启动失败，请使用 USB" : "电脑启动音乐桥接程序") : s->lyric[0] ? s->lyric : s->message);
    text(line3, s->connected ? s->after : "");
    lv_bar_set_value(progress, s->connected && s->duration > 0 ? (int)((int64_t)s->position * 1000 / s->duration) : 0, LV_ANIM_OFF);
    if (s->connected) {
        char vol[16];
        if (s->volume < 0) snprintf(vol, sizeof(vol), "--");
        else snprintf(vol, sizeof(vol), "%d%%", s->volume);
        snprintf(b, sizeof(b), "%02d:%02d / %02d:%02d  音量 %s", s->position / 60000,
            s->position / 1000 % 60, s->duration / 60000, s->duration / 1000 % 60, vol);
        if (!s->duration) snprintf(b, sizeof(b), "进度不可用   音量 %s", vol);
    } else snprintf(b, sizeof(b), "蓝牙无线连接 / USB 调试");
    text(volume, b);
    if (s->connected && s->desktop_lyrics>=0)
        text(footer,s->desktop_lyrics?"桌面歌词：开启":"桌面歌词：关闭");
    else text(footer,"");
}
