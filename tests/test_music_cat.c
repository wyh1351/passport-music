#include "music_cat.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    for (uint32_t t=0;t<10000;t+=100) {
        music_cat_pose_t resting=music_cat_pose(t,false),playing=music_cat_pose(t,true);
        assert(resting.closed && resting.dy==0);
        assert(playing.dy==0 || playing.dy==1);
        assert(playing.closed==(t%5000>=4700));
    }
    assert(music_cat_pose(600,true).dy==1);
    assert(music_cat_pose(1200,true).dy==0);
    assert(!music_cat_pose(5000,true).closed);
    assert(music_cat_pose(UINT32_MAX,true).dy<=1);
    puts("Music cat: playback motion, blink, rest and bounded displacement PASS");
    return 0;
}
