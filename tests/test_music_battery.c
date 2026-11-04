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
    assert(music_battery_display_soc(49)==50);
    assert(music_battery_display_soc(50)==51);
    assert(music_battery_display_soc(97)==99);
    assert(music_battery_display_soc(98)==100);
    assert(music_battery_display_soc(99)==100);
    assert(music_battery_display_soc(100)==100);
    int previous=0;
    for (int raw=0;raw<=100;++raw) {
        int display=music_battery_display_soc(raw);
        assert(display>=previous && display<=100 && display-previous<=2);
        if (raw<MUSIC_BATTERY_FULL_SOC) assert(display<100);
        previous=display;
    }
    puts("Battery display: calibrated endpoint, rounding, monotonicity and unavailable readings PASS");
    return 0;
}
