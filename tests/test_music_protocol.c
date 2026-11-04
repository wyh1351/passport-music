#include "music_protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
int main(void) {
    assert(music_json_flat("{\"title\":\"a{b}\\\"[]\"}"));
    assert(!music_json_flat("{\"a\":{\"b\":0}}"));
    assert(!music_json_flat("[1,2,3]"));
    assert(!music_json_flat("{\"title\":\"open"));
    assert(music_key_action(0, false, false) == MUSIC_VOLUME_UP);
    assert(music_key_action(1, false, false) == MUSIC_VOLUME_DOWN);
    assert(music_key_action(0, false, true) == MUSIC_VOLUME_UP_20);
    assert(music_key_action(1, false, true) == MUSIC_VOLUME_DOWN_20);
    assert(music_key_action(0, true, true) == MUSIC_PREVIOUS);
    assert(music_key_action(1, true, true) == MUSIC_NEXT);
    assert(music_key_action(0, true, false) == MUSIC_PREVIOUS);
    assert(music_key_action(1, true, false) == MUSIC_NEXT);
    assert(music_key_action(2, false, false) == MUSIC_TOGGLE);
    assert(music_key_action(2, true, false) == MUSIC_SETTINGS);
    assert(music_key_action(2, false, true) == MUSIC_DESKTOP_LYRICS);
    assert(music_key_action(3, false, false) == MUSIC_NONE);
    assert(!strcmp(music_action_name(MUSIC_LYRIC_PREVIOUS),"lyric_previous"));
    assert(!strcmp(music_action_name(MUSIC_LYRIC_NEXT),"lyric_next"));
    assert(!strcmp(music_action_name(MUSIC_DESKTOP_LYRICS),"toggle_desktop_lyrics"));
    assert(!strcmp(music_action_name(MUSIC_VOLUME_UP_20),"volume_up_20"));
    assert(!strcmp(music_action_name(MUSIC_VOLUME_DOWN_20),"volume_down_20"));
    assert(!strcmp(music_action_name(MUSIC_SETTINGS),""));
    assert(music_offset_adjust(0,1,false)==50);
    assert(music_offset_adjust(0,-1,true)==-250);
    assert(music_offset_adjust(1950,1,true)==2000);
    assert(music_offset_adjust(-1950,-1,true)==-2000);
    assert(music_offset_adjust(INT_MAX,1,true)==2000);
    assert(music_offset_adjust(INT_MIN,-1,true)==-2000);
    assert(music_offset_valid(0) && music_offset_valid(-2000) && music_offset_valid(2000));
    assert(!music_offset_valid(2001) && !music_offset_valid(-2001) && !music_offset_valid(51));
    char out[16];
    char symbols[128];
    const char *sample="A·B •‧∙⋅・ ‘x’ “y” —… ±℃ ♪♫♭♯ café";
    music_text_copy(symbols,sizeof(symbols),sample); assert(!strcmp(symbols,sample));
    music_text_copy(out,5,"A·中"); assert(!strcmp(out,"A·"));
    music_text_copy(out, 5, "中文"); assert(!strcmp(out, "中"));
    music_text_copy(out, sizeof(out), "A\xf0\x9f\x8e\xb5" "中"); assert(!strcmp(out, "A?中"));
    music_text_copy(out, sizeof(out), "\xed\xa0\x80"); assert(!strcmp(out, "???"));
    music_text_copy(out, sizeof(out), "\xe4\xb8"); assert(!strcmp(out, "??"));
    music_text_copy(out, sizeof(out), "\xe9\xbf\xb0"); assert(!strcmp(out, "?")); // absent U+9FF0
    music_text_copy(out, 1, "中文"); assert(out[0] == 0);
    music_framer_t f={0};
    for (int i=0;i<100;i++) assert(!music_framer_feed(&f,'A',out,sizeof(out)));
    assert(!music_framer_feed(&f,'\n',out,sizeof(out)));
    assert(!music_framer_feed(&f,'O',out,sizeof(out)));
    assert(!music_framer_feed(&f,'K',out,sizeof(out)));
    assert(music_framer_feed(&f,'\n',out,sizeof(out))); assert(!strcmp(out,"OK"));
    assert(!music_framer_feed(&f,0,out,sizeof(out)));
    assert(!music_framer_feed(&f,'\n',out,sizeof(out)));
    puts("Music protocol: PASS"); return 0;
}
