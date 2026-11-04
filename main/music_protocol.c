#include "music_protocol.h"
#include "../assets/fonts/music_font_coverage.h"
#include <string.h>
music_action_t music_key_action(int key, bool held, bool twice) {
    if (key == 2) return held ? MUSIC_SETTINGS : twice ? MUSIC_DESKTOP_LYRICS : MUSIC_TOGGLE;
    if (key == 0) return held ? MUSIC_PREVIOUS : twice ? MUSIC_VOLUME_UP_20 : MUSIC_VOLUME_UP;
    if (key == 1) return held ? MUSIC_NEXT : twice ? MUSIC_VOLUME_DOWN_20 : MUSIC_VOLUME_DOWN;
    return MUSIC_NONE;
}
bool music_offset_valid(int value) {
    return value>=-MUSIC_OFFSET_LIMIT_MS && value<=MUSIC_OFFSET_LIMIT_MS && value%50==0;
}
int music_offset_adjust(int value, int direction, bool large_step) {
    int64_t next=(int64_t)value+(direction>0?1:direction<0?-1:0)*(large_step?250:50);
    if (next>MUSIC_OFFSET_LIMIT_MS) return MUSIC_OFFSET_LIMIT_MS;
    if (next<-MUSIC_OFFSET_LIMIT_MS) return -MUSIC_OFFSET_LIMIT_MS;
    return (int)next;
}
const char *music_action_name(music_action_t action) {
    static const char *names[] = {"", "volume_up", "volume_down", "previous", "next", "toggle", "lyric_previous", "lyric_next", "toggle_desktop_lyrics", "volume_up_20", "volume_down_20"};
    return action >= MUSIC_NONE && action <= MUSIC_VOLUME_DOWN_20 ? names[action] : "";
}
bool music_json_flat(const char *json) {
    bool quoted=false, escape=false;
    int depth=0;
    for (const char *p=json; *p; ++p) {
        if (quoted) {
            if (escape) escape=false;
            else if (*p=='\\') escape=true;
            else if (*p=='"') quoted=false;
        } else {
            if (*p=='"') quoted=true;
            else if (*p=='[' || *p==']') return false;
            else if (*p=='{') { if (++depth>1) return false; }
            else if (*p=='}') { if (--depth<0) return false; }
        }
    }
    return !quoted && depth==0;
}
void music_text_copy(char *dst, size_t size, const char *src) {
    if (!size) return;
    size_t used = 0;
    const unsigned char *p = (const unsigned char *)src;
    while (*p) {
        uint32_t cp = *p;
        size_t n = 1;
        if (*p >= 0xc2 && *p <= 0xdf) { n = 2; cp = *p & 0x1f; }
        else if (*p >= 0xe0 && *p <= 0xef) { n = 3; cp = *p & 0x0f; }
        else if (*p >= 0xf0 && *p <= 0xf4) { n = 4; cp = *p & 7; }
        bool valid = *p < 0x80 || n > 1;
        for (size_t i = 1; i < n; ++i) {
            if ((p[i] & 0xc0) != 0x80) { valid = false; break; }
            cp = (cp << 6) | (p[i] & 0x3f);
        }
        valid = valid && !(n == 2 && cp < 0x80) && !(n == 3 && cp < 0x800)
            && !(n == 4 && cp < 0x10000) && cp <= 0x10ffff && !(cp >= 0xd800 && cp <= 0xdfff);
        bool supported = valid && music_font_supported(cp);
        if (!supported) {
            if (used + 1 >= size) break;
            dst[used++] = '?'; p += valid ? n : 1;
        } else {
            if (used + n >= size) break;
            memcpy(dst + used, p, n); used += n; p += n;
        }
    }
    dst[used] = 0;
}
bool music_framer_feed(music_framer_t *f, uint8_t byte, char *out, size_t size) {
    if (byte == '\n') {
        bool ready = !f->dropping && f->used != 0;
        if (size) out[f->used < size ? f->used : 0] = 0;
        f->used = 0; f->dropping = false;
        return ready;
    }
    if (byte == '\r') return false;
    if (!byte || f->used + 1 >= size) f->dropping = true;
    if (!f->dropping) out[f->used++] = (char)byte;
    return false;
}
