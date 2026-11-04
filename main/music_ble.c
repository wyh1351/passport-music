// Application BLE transport, deliberately separate from the reusable BSP.
#include <stdbool.h>
#include "music_ble.h"
#include "esp_random.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "host/ble_hs.h"
#include "host/ble_att.h"
#include "host/ble_gap.h"
#include "host/ble_gatt.h"
#include "host/ble_hs_mbuf.h"
#include "host/ble_sm.h"
#include "host/ble_store.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "os/os_mbuf.h"
#include <stdatomic.h>
#include <string.h>

// Nordic UART service: PC writes RX, firmware notifies TX. All writes require
// authenticated encryption; the six digit passkey is shown on the device only.
static const ble_uuid128_t service = BLE_UUID128_INIT(0x9e,0xca,0xdc,0x24,0x0e,0xe5,0xa9,0xe0,0x93,0xf3,0xa3,0xb5,0x01,0x00,0x40,0x6e);
static const ble_uuid128_t rx = BLE_UUID128_INIT(0x9e,0xca,0xdc,0x24,0x0e,0xe5,0xa9,0xe0,0x93,0xf3,0xa3,0xb5,0x02,0x00,0x40,0x6e);
static const ble_uuid128_t tx = BLE_UUID128_INIT(0x9e,0xca,0xdc,0x24,0x0e,0xe5,0xa9,0xe0,0x93,0xf3,0xa3,0xb5,0x03,0x00,0x40,0x6e);
static QueueHandle_t chunks;
static atomic_uint connection = ATOMIC_VAR_INIT(BLE_HS_CONN_HANDLE_NONE);
static atomic_uint passkey = ATOMIC_VAR_INIT(1000000);
static atomic_bool secure, subscribed;
static uint16_t tx_handle;
static uint8_t addr_type;
static const char *TAG="music_ble";
static int gap(struct ble_gap_event *event, void *arg);
void ble_store_config_init(void);

static int access_cb(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctx, void *arg) {
    (void)conn; (void)attr; (void)arg;
    if (ctx->op != BLE_GATT_ACCESS_OP_WRITE_CHR) return BLE_ATT_ERR_READ_NOT_PERMITTED;
    music_ble_chunk_t chunk;
    uint16_t len = OS_MBUF_PKTLEN(ctx->om);
    if (!len || len > sizeof(chunk.data)) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
    chunk.length = len;
    if (ble_hs_mbuf_to_flat(ctx->om, chunk.data, sizeof(chunk.data), NULL)) return BLE_ATT_ERR_UNLIKELY;
    // Write-with-response allows the PC to back off instead of silently dropping bytes.
    return xQueueSend(chunks, &chunk, 0) == pdTRUE ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}
static const struct ble_gatt_svc_def services[] = {
    {.type = BLE_GATT_SVC_TYPE_PRIMARY, .uuid = &service.u,
     .characteristics = (struct ble_gatt_chr_def[]) {
        {.uuid = &rx.u, .access_cb = access_cb,
         .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_ENC | BLE_GATT_CHR_F_WRITE_AUTHEN},
        {.uuid = &tx.u, .access_cb = access_cb, .val_handle = &tx_handle,
         .flags = BLE_GATT_CHR_F_NOTIFY}, {0}}}, {0}
};
static void advertise(void) {
    struct ble_hs_adv_fields fields = {0}, scan = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.uuids128 = (ble_uuid128_t *)&service; fields.num_uuids128 = 1; fields.uuids128_is_complete = 1;
    scan.name = (const uint8_t *)"Passport Music"; scan.name_len = 14; scan.name_is_complete = 1;
    if (ble_gap_adv_set_fields(&fields) || ble_gap_adv_rsp_set_fields(&scan)) return;
    struct ble_gap_adv_params params = {0};
    params.conn_mode = BLE_GAP_CONN_MODE_UND; params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    (void)ble_gap_adv_start(addr_type, NULL, BLE_HS_FOREVER, &params, gap, NULL);
}
static int gap(struct ble_gap_event *e, void *arg) {
    (void)arg;
    switch (e->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (e->connect.status) advertise();
        else {
            atomic_store(&connection, e->connect.conn_handle);
            atomic_store(&secure, false); atomic_store(&subscribed, false);
            (void)ble_gap_security_initiate(e->connect.conn_handle);
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        atomic_store(&connection, BLE_HS_CONN_HANDLE_NONE);
        atomic_store(&secure, false); atomic_store(&subscribed, false);
        atomic_store(&passkey, 1000000);
        // Do not reset the queue while the worker may be consuming it. New
        // snapshots always start with a newline to discard a partial old frame.
        advertise(); break;
    case BLE_GAP_EVENT_SUBSCRIBE:
        if (e->subscribe.attr_handle == tx_handle) atomic_store(&subscribed, e->subscribe.cur_notify);
        break;
    case BLE_GAP_EVENT_ENC_CHANGE: {
        struct ble_gap_conn_desc desc;
        bool ok = !e->enc_change.status && !ble_gap_conn_find(e->enc_change.conn_handle, &desc)
            && desc.sec_state.encrypted && desc.sec_state.authenticated;
        atomic_store(&secure, ok);
        if (ok) atomic_store(&passkey, 1000000);
        else if (e->enc_change.status) {
            ESP_LOGW(TAG,"Encryption failed: status=%d; disconnecting for retry",e->enc_change.status);
            (void)ble_gap_terminate(e->enc_change.conn_handle,BLE_ERR_AUTH_FAIL);
        }
        break;
    }
    case BLE_GAP_EVENT_REPEAT_PAIRING: {
        // Windows can forget its bond while this device retains it. NimBLE
        // otherwise silently rejects its new pairing request. Remove only the
        // requesting peer's stale bond, then repeat the normal authenticated
        // six-digit pairing; never erase the NVS partition or other peers.
        struct ble_gap_conn_desc desc;
        int rc=ble_gap_conn_find(e->repeat_pairing.conn_handle,&desc);
        if (rc) {
            ESP_LOGW(TAG,"Repeat pairing lookup failed: %d",rc);
            return BLE_GAP_REPEAT_PAIRING_IGNORE;
        }
        rc=ble_store_util_delete_peer(&desc.peer_id_addr);
        if (rc) {
            ESP_LOGW(TAG,"Stale peer bond removal failed: %d",rc);
            return BLE_GAP_REPEAT_PAIRING_IGNORE;
        }
        atomic_store(&secure,false); atomic_store(&subscribed,false);
        atomic_store(&passkey,1000000);
        ESP_LOGI(TAG,"Stale peer bond removed; retrying authenticated pairing");
        return BLE_GAP_REPEAT_PAIRING_RETRY;
    }
    case BLE_GAP_EVENT_PASSKEY_ACTION:
        if (e->passkey.params.action == BLE_SM_IOACT_DISP) {
            struct ble_sm_io io = {.action = BLE_SM_IOACT_DISP, .passkey = esp_random() % 1000000};
            atomic_store(&passkey, io.passkey);
            (void)ble_sm_inject_io(e->passkey.conn_handle, &io);
        }
        break;
    default: break;
    }
    return 0;
}
static void sync_cb(void) {
    if (!ble_hs_util_ensure_addr(0) && !ble_hs_id_infer_auto(0, &addr_type)) advertise();
}
static void host(void *arg) { (void)arg; nimble_port_run(); vTaskDelete(NULL); }
esp_err_t music_ble_start(void) {
    chunks = xQueueCreate(20, sizeof(music_ble_chunk_t));
    if (!chunks) return ESP_ERR_NO_MEM;
    esp_err_t err = nimble_port_init();
    if (err != ESP_OK) { vQueueDelete(chunks); chunks = NULL; return err; }
    ble_hs_cfg.sync_cb = sync_cb;
    ble_hs_cfg.sm_io_cap = BLE_SM_IO_CAP_DISP_ONLY;
    ble_hs_cfg.sm_bonding = 1; ble_hs_cfg.sm_mitm = 1; ble_hs_cfg.sm_sc = 1;
    ble_hs_cfg.sm_our_key_dist = BLE_SM_PAIR_KEY_DIST_ENC | BLE_SM_PAIR_KEY_DIST_ID;
    ble_hs_cfg.sm_their_key_dist = BLE_SM_PAIR_KEY_DIST_ENC | BLE_SM_PAIR_KEY_DIST_ID;
    ble_hs_cfg.store_status_cb = ble_store_util_status_rr;
    ble_store_config_init();
    ble_svc_gap_init(); ble_svc_gatt_init();
    int rc = ble_svc_gap_device_name_set("Passport Music");
    if (!rc) rc = ble_gatts_count_cfg(services);
    if (!rc) rc = ble_gatts_add_svcs(services);
    if (rc || xTaskCreate(host, "music_ble", 4096, NULL, 5, NULL) != pdPASS) {
        (void)nimble_port_deinit(); vQueueDelete(chunks); chunks = NULL; return ESP_FAIL;
    }
    return ESP_OK;
}
bool music_ble_receive(music_ble_chunk_t *chunk) { return chunks && xQueueReceive(chunks, chunk, 0) == pdTRUE; }
unsigned music_ble_passkey(void) { return atomic_load(&passkey); }
bool music_ble_send(const char *data, size_t length) {
    unsigned conn = atomic_load(&connection);
    if (conn == BLE_HS_CONN_HANDLE_NONE || !atomic_load(&secure) || !atomic_load(&subscribed)) return false;
    // Fragment commands even on the default 23-byte MTU. Partial commands have
    // no effect; a newline before the next command recovers the receiver.
    size_t payload = ble_att_mtu(conn) - 3;
    struct os_mbuf *reset = ble_hs_mbuf_from_flat("\n", 1);
    if (!reset || ble_gatts_notify_custom(conn, tx_handle, reset)) return false;
    for (size_t offset=0; offset<length; offset+=payload) {
        size_t n = length-offset < payload ? length-offset : payload;
        struct os_mbuf *om = ble_hs_mbuf_from_flat(data+offset, n);
        if (!om || ble_gatts_notify_custom(conn, tx_handle, om)) return false;
    }
    return true;
}
