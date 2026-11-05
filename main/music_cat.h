#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef struct { bool closed; int dy; } music_cat_pose_t;
// Driven only by visible UI updates; no separate timer or task runs while asleep.
static inline music_cat_pose_t music_cat_pose(uint32_t now_ms,bool playing) {
    if (!playing) return (music_cat_pose_t){.closed=true,.dy=0};
    return (music_cat_pose_t){.closed=now_ms%5000>=4700,.dy=(int)(now_ms/600%2)};
}
