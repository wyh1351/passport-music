#include "music_battery.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
int main(void) {
    assert(music_battery_display_soc(-1)==-1);
    assert(music_battery_display_soc(INT_MIN)==-1);
    assert(music_battery_display_soc(INT_MAX)==-1);
    assert(music_battery_display_soc(101)==-1);
    assert(music_battery_display_soc(0)==0);
    assert(music_battery_display_soc(1)==1);
    assert(music_battery_display_soc(49)==49);
    assert(music_battery_display_soc(50)==50);
    assert(music_battery_display_soc(97)==97);
    assert(music_battery_display_soc(98)==98);
    assert(music_battery_display_soc(99)==99);
    assert(music_battery_display_soc(100)==100);
    for (int raw=0;raw<=100;++raw) {
        int display=music_battery_display_soc(raw);
        assert(display==raw);
    }
    puts("Battery display: raw 0-100 identity and unavailable readings PASS");
    return 0;
}
