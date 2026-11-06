// One worker owns state, framing and input; button callbacks enqueue only.
#include "bsp_display.h"
#include "bsp_button.h"
#include "bsp_i2c.h"
#include "bsp_battery.h"
#include "driver/usb_serial_jtag.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "music_protocol.h"
#include "music_ui.h"
#include "music_ble.h"
#include "music_settings.h"
#include "key_guard.h"
#include "bsp_pins.h"
#include "cJSON.h"
#include <stdio.h>
#include <string.h>
typedef struct { bsp_btn_t key; bsp_btn_ev_t event; } input_t;
static QueueHandle_t keys;
static music_state_t state={.brightness=75,.screen_seconds=60,.desktop_lyrics=-1};
static char frames[2][MUSIC_FRAME_MAX];
static music_framer_t framers[2];
static uint32_t command_id;
static uint32_t boot_id;
static key_guard_t s_key_guard;
static volatile bool s_input_ready;
static bool ble_ready;
static nvs_handle_t settings_nvs;
static bool settings_store_ready;
static bool settings_dirty;
static int64_t save_at;

static void preferences_changed(int64_t now) {
    state.save_status=settings_store_ready?MUSIC_SAVE_PENDING:MUSIC_SAVE_ERROR;
    settings_dirty=settings_store_ready;
    save_at=now+1000000;
}
static void save_preferences(int64_t now) {
    if (!settings_dirty || now<save_at) return;
    esp_err_t err=nvs_set_i32(settings_nvs,"offset_ms",state.lyric_offset_ms);
    if (err==ESP_OK) err=nvs_set_i32(settings_nvs,"brightness",state.brightness);
    if (err==ESP_OK) err=nvs_set_i32(settings_nvs,"screen_secs",state.screen_seconds);
    if (err==ESP_OK) err=nvs_set_i32(settings_nvs,"pet",state.pet);
    if (err==ESP_OK) err=nvs_set_i32(settings_nvs,"wallpaper",state.wallpaper);
    if (err==ESP_OK) err=nvs_commit(settings_nvs);
    state.save_status=err==ESP_OK?MUSIC_SAVE_OK:MUSIC_SAVE_ERROR;
    settings_dirty=err!=ESP_OK;
    save_at=now+5000000;
}

static void on_key(bsp_btn_t key, bsp_btn_ev_t event, void *arg) {
    (void)arg;
    if (key_guard_consume(&s_key_guard, event == BSP_BTN_RELEASE, esp_timer_get_time())) return;
    if (!s_input_ready) return;
    const input_t input = {key, event};
    if (keys) (void)xQueueSend(keys, &input, 0);
}
static bool read_state(const char *line) {
    if (strncmp(line, "FAPM1 ", 6)) return false;
    // Bound cJSON recursion independently of its library-wide nesting limit.
    if (!music_json_flat(line+6)) return false;
    cJSON *root = cJSON_ParseWithOpts(line + 6, NULL, true);
    if (!root || !cJSON_IsObject(root)) { cJSON_Delete(root); return false; }
    const cJSON *type = cJSON_GetObjectItemCaseSensitive(root, "type");
    bool valid = cJSON_IsString(type) && !strcmp(type->valuestring, "state");
    if (valid) {
        music_state_t next = {.desktop_lyrics=-1};
        const char *names[] = {"title", "artist", "album", "lyric", "before", "after", "message"};
        char *dest[] = {next.title, next.artist, next.album, next.lyric, next.before, next.after, next.message};
        const size_t sizes[] = {sizeof(next.title), sizeof(next.artist), sizeof(next.album),
            sizeof(next.lyric), sizeof(next.before), sizeof(next.after), sizeof(next.message)};
        for (size_t i = 0; i < 7; ++i) {
            const cJSON *s = cJSON_GetObjectItemCaseSensitive(root, names[i]);
            if (!cJSON_IsString(s)) { valid = false; break; }
            music_text_copy(dest[i], sizes[i], s->valuestring);
        }
        const char *nums[] = {"position", "duration", "volume"};
        int *values[] = {&next.position, &next.duration, &next.volume};
        for (size_t i = 0; i < 3 && valid; ++i) {
            const cJSON *n = cJSON_GetObjectItemCaseSensitive(root, nums[i]);
            if (!cJSON_IsNumber(n) || n->valuedouble < -1 || n->valuedouble > 86400000) valid = false;
            else *values[i] = n->valueint;
        }
        const cJSON *playing = cJSON_GetObjectItemCaseSensitive(root, "playing");
        const cJSON *available = cJSON_GetObjectItemCaseSensitive(root, "available");
        valid = valid && cJSON_IsBool(playing) && cJSON_IsBool(available)
            && next.volume >= -1 && next.volume <= 100 && next.position >= 0 && next.duration >= 0;
        if (valid) {
            next.playing = cJSON_IsTrue(playing); next.available = cJSON_IsTrue(available);
            next.connected = true;
            music_preferences_copy(&next,&state);
            const cJSON *ack=cJSON_GetObjectItemCaseSensitive(root,"lyric_offset_ack");
            if (cJSON_IsNumber(ack) && ack->valuedouble==ack->valueint && music_offset_valid(ack->valueint)) {
                next.offset_supported=true; next.offset_ack=ack->valueint;
            }
            const cJSON *desktop=cJSON_GetObjectItemCaseSensitive(root,"desktop_lyrics");
            if (cJSON_IsNumber(desktop) && (desktop->valuedouble==0 || desktop->valuedouble==1))
                next.desktop_lyrics=desktop->valueint;
            state = next;
        }
    }
    cJSON_Delete(root);
    return valid;
}
static void worker(void *arg) {
    (void)arg;
    int64_t last_rx = 0, battery_at = 0, render_at = 0;
    int battery = -1, transport = -1, applied_brightness=-1;
    music_screen_t screen={.activity_at=esp_timer_get_time()};
    int64_t settings_at=0;
    for (;;) {
        unsigned char bytes[128];
        int n = usb_serial_jtag_read_bytes(bytes, sizeof(bytes), pdMS_TO_TICKS(20));
        for (int i = 0; i < n; ++i) {
            if (music_framer_feed(&framers[0], bytes[i], frames[0], MUSIC_FRAME_MAX) && read_state(frames[0])) {
                last_rx = esp_timer_get_time(); transport = 0;
            }
        }
        music_ble_chunk_t chunk;
        // Bound work per loop so continuous traffic cannot starve input/UI.
        for (int count = 0; count < 20 && music_ble_receive(&chunk); ++count) {
            for (unsigned i = 0; i < chunk.length; ++i) {
                if (music_framer_feed(&framers[1], chunk.data[i], frames[1], MUSIC_FRAME_MAX) && read_state(frames[1])) {
                    last_rx = esp_timer_get_time(); transport = 1;
                }
            }
        }
        int64_t now = esp_timer_get_time();
        state.connected = last_rx != 0 && now - last_rx < 4000000;
        input_t input;
        while (xQueueReceive(keys, &input, 0) == pdTRUE) {
            bool actionable=input.event==BSP_BTN_CLICK || input.event==BSP_BTN_LONG || input.event==BSP_BTN_DOUBLE;
            bool was_off=screen.off;
            bool consumed=music_screen_input(&screen,now,input.event==BSP_BTN_PRESS,input.event==BSP_BTN_RELEASE,actionable);
            if (was_off && !screen.off) render_at=0;
            if (consumed || !actionable) continue;
            if (state.settings_page) {
                unsigned result=music_settings_input(&state,input.key,input.event==BSP_BTN_LONG,input.event==BSP_BTN_DOUBLE);
                if (result&MUSIC_PREF_CHANGED) { preferences_changed(now); settings_at=0; }
                if (result&MUSIC_PREF_SAVE) { save_at=0; save_preferences(now); }
                render_at=0;
                continue;
            }
            music_action_t action = music_key_action(input.key, input.event == BSP_BTN_LONG, input.event == BSP_BTN_DOUBLE);
            if (action==MUSIC_SETTINGS) {
                state.settings_page=true; state.settings_edit=false; render_at=0;
            } else if (action != MUSIC_NONE && state.connected &&
                       (state.available || action==MUSIC_DESKTOP_LYRICS)) {
                char out[128];
                int len = snprintf(out, sizeof(out), "FAPM1 {\"type\":\"command\",\"boot\":%lu,\"id\":%lu,\"action\":\"%s\"}\n",
                    (unsigned long)boot_id, (unsigned long)++command_id, music_action_name(action));
                if (transport == 1) (void)music_ble_send(out, len);
                else (void)usb_serial_jtag_write_bytes(out, len, pdMS_TO_TICKS(50));
            }
        }
        save_preferences(now);
        if (state.connected && now>=settings_at) {
            char out[128];
            int len=snprintf(out,sizeof(out),"FAPM1 {\"type\":\"settings\",\"boot\":%lu,\"lyric_offset_ms\":%d}\n",
                (unsigned long)boot_id,state.lyric_offset_ms);
            if (transport==1) (void)music_ble_send(out,len);
            else if (transport==0) (void)usb_serial_jtag_write_bytes(out,len,pdMS_TO_TICKS(50));
            settings_at=now+1000000;
        }
        if (now >= battery_at) { battery = bsp_battery_soc(); battery_at = now + 30000000; }
        unsigned passkey=ble_ready?music_ble_passkey():1000001;
        bool was_off=screen.off;
        music_screen_tick(&screen,now,state.screen_seconds,passkey<1000000);
        if (was_off && !screen.off) render_at=0;
        if (!screen.off && now >= render_at && bsp_lvgl_lock(100)) {
            music_ui_update(&state, battery, passkey);
            bsp_lvgl_unlock(); render_at = now + 200000;
        }
        int brightness=screen.off?0:state.brightness;
        if (brightness!=applied_brightness) { bsp_display_backlight(brightness); applied_brightness=brightness; }
    }
}
void app_main(void) {
    // A key held across boot must be released before it becomes a music command.
    key_guard_arm(&s_key_guard, esp_timer_get_time(), 10000000);
    ESP_ERROR_CHECK(bsp_i2c_init());
    ESP_ERROR_CHECK(bsp_display_init());
    ESP_ERROR_CHECK(bsp_lvgl_init() ? ESP_OK : ESP_FAIL);
    (void)bsp_battery_init();
    usb_serial_jtag_driver_config_t usb = {.tx_buffer_size = 1024, .rx_buffer_size = MUSIC_FRAME_MAX};
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    keys = xQueueCreate(16, sizeof(input_t));
    ESP_ERROR_CHECK(keys ? ESP_OK : ESP_ERR_NO_MEM);
    if (!bsp_lvgl_lock(1000)) abort();
    music_ui_create(); bsp_lvgl_unlock();
    // Never erase stored data to hide an NVS error; USB remains usable on BLE failure.
    if (nvs_flash_init() == ESP_OK) {
        settings_store_ready=nvs_open("music_remote",NVS_READWRITE,&settings_nvs)==ESP_OK;
        int32_t value=0;
        if (settings_store_ready && nvs_get_i32(settings_nvs,"offset_ms",&value)==ESP_OK && music_offset_valid(value)) state.lyric_offset_ms=value;
        if (settings_store_ready && nvs_get_i32(settings_nvs,"brightness",&value)==ESP_OK && music_brightness_valid(value)) state.brightness=value;
        if (settings_store_ready && nvs_get_i32(settings_nvs,"screen_secs",&value)==ESP_OK && music_screen_seconds_valid(value)) state.screen_seconds=value;
        if (settings_store_ready && nvs_get_i32(settings_nvs,"pet",&value)==ESP_OK && music_pet_valid(value)) state.pet=(music_pet_t)value;
        if (settings_store_ready && nvs_get_i32(settings_nvs,"wallpaper",&value)==ESP_OK && music_wallpaper_valid(value)) state.wallpaper=value;
        if (!settings_store_ready) state.save_status=MUSIC_SAVE_ERROR;
        ble_ready=music_ble_start()==ESP_OK;
    } else state.save_status=MUSIC_SAVE_ERROR;
    ESP_ERROR_CHECK(bsp_button_init(on_key, NULL));
    key_guard_sync_released(&s_key_guard, bsp_button_read_mv() >= BSP_BTN_MV_RELEASED_MIN);
    // USB Serial/JTAG can survive a CPU reset. Scope deduplication to this boot.
    boot_id=esp_random();
    ESP_ERROR_CHECK(xTaskCreate(worker, "music_bridge", 8192, NULL, 4, NULL) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    s_input_ready = true;
}
