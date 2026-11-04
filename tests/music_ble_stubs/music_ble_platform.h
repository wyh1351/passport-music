#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_NO_MEM 0x101
#define ESP_LOGI(tag,...) ((void)(tag))
#define ESP_LOGW(tag,...) ((void)(tag))
typedef void *QueueHandle_t;
#define pdTRUE 1
#define pdPASS 1
#define BLE_HS_CONN_HANDLE_NONE 65535
#define BLE_HS_FOREVER 0
#define BLE_HS_ADV_F_DISC_GEN 2
#define BLE_HS_ADV_F_BREDR_UNSUP 4
#define BLE_GAP_CONN_MODE_UND 2
#define BLE_GAP_DISC_MODE_GEN 2
#define BLE_GAP_EVENT_CONNECT 0
#define BLE_GAP_EVENT_DISCONNECT 1
#define BLE_GAP_EVENT_ENC_CHANGE 10
#define BLE_GAP_EVENT_PASSKEY_ACTION 11
#define BLE_GAP_EVENT_SUBSCRIBE 14
#define BLE_GAP_EVENT_REPEAT_PAIRING 17
#define BLE_GAP_REPEAT_PAIRING_RETRY 1
#define BLE_GAP_REPEAT_PAIRING_IGNORE 2
#define BLE_ERR_AUTH_FAIL 5
#define BLE_SM_IOACT_DISP 3
#define BLE_SM_IO_CAP_DISP_ONLY 0
#define BLE_SM_PAIR_KEY_DIST_ENC 1
#define BLE_SM_PAIR_KEY_DIST_ID 2
#define BLE_ATT_ERR_READ_NOT_PERMITTED 2
#define BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN 13
#define BLE_ATT_ERR_UNLIKELY 14
#define BLE_ATT_ERR_INSUFFICIENT_RES 17
#define BLE_GATT_ACCESS_OP_WRITE_CHR 2
#define BLE_GATT_SVC_TYPE_PRIMARY 1
#define BLE_GATT_CHR_F_WRITE 8
#define BLE_GATT_CHR_F_WRITE_ENC 512
#define BLE_GATT_CHR_F_WRITE_AUTHEN 1024
#define BLE_GATT_CHR_F_NOTIFY 16
typedef struct {uint8_t type;} ble_uuid_t;
typedef struct {ble_uuid_t u;uint8_t value[16];} ble_uuid128_t;
#define BLE_UUID128_INIT(...) {.u={0},.value={__VA_ARGS__}}
typedef struct {uint8_t type,val[6];} ble_addr_t;
struct os_mbuf {uint16_t len;};
#define OS_MBUF_PKTLEN(om) ((om)->len)
struct ble_gatt_access_ctxt {int op;struct os_mbuf *om;};
struct ble_gatt_chr_def {const ble_uuid_t *uuid;int (*access_cb)(uint16_t,uint16_t,struct ble_gatt_access_ctxt *,void *);unsigned flags;uint16_t *val_handle;};
struct ble_gatt_svc_def {int type;const ble_uuid_t *uuid;struct ble_gatt_chr_def *characteristics;};
struct ble_hs_adv_fields {int flags;ble_uuid128_t *uuids128;int num_uuids128;bool uuids128_is_complete;const uint8_t *name;int name_len;bool name_is_complete;};
struct ble_gap_adv_params {int conn_mode,disc_mode;};
struct ble_gap_conn_desc {ble_addr_t peer_id_addr;struct {bool encrypted,authenticated;} sec_state;};
struct ble_gap_event {int type;union {
    struct {int status;uint16_t conn_handle;} connect,enc_change;
    struct {uint16_t attr_handle;bool cur_notify;} subscribe;
    struct {uint16_t conn_handle;} repeat_pairing;
    struct {uint16_t conn_handle;struct {int action;} params;} passkey;
};};
struct ble_sm_io {int action;uint32_t passkey;};
static struct {void (*sync_cb)(void);int sm_io_cap,sm_bonding,sm_mitm,sm_sc,sm_our_key_dist,sm_their_key_dist;int (*store_status_cb)(int,void *);} ble_hs_cfg;
static int test_lookup_result,test_delete_result,test_delete_calls,test_terminate_calls,test_advertisements;
static uint16_t test_looked_up,test_terminated;
static int test_terminate_reason;
static ble_addr_t test_deleted;
static struct ble_gap_conn_desc test_desc;
static inline int ble_gap_conn_find(uint16_t h,struct ble_gap_conn_desc *d){test_looked_up=h;if(!test_lookup_result)*d=test_desc;return test_lookup_result;}
static inline int ble_store_util_delete_peer(const ble_addr_t *a){test_deleted=*a;++test_delete_calls;return test_delete_result;}
static inline int ble_gap_terminate(uint16_t h,int reason){test_terminated=h;test_terminate_reason=reason;++test_terminate_calls;return 0;}
static inline int ble_gap_adv_set_fields(const struct ble_hs_adv_fields *f){(void)f;return 0;}
static inline int ble_gap_adv_rsp_set_fields(const struct ble_hs_adv_fields *f){(void)f;return 0;}
static inline int ble_gap_adv_start(uint8_t t,const void *a,int duration,const struct ble_gap_adv_params *p,int (*cb)(struct ble_gap_event *,void *),void *arg){(void)t;(void)a;(void)duration;(void)p;(void)cb;(void)arg;++test_advertisements;return 0;}
static inline int ble_gap_security_initiate(uint16_t h){(void)h;return 0;}
static inline uint32_t esp_random(void){return 123456;}
static inline int ble_sm_inject_io(uint16_t h,const struct ble_sm_io *io){(void)h;(void)io;return 0;}
static inline int ble_store_util_status_rr(int event,void *arg){(void)event;(void)arg;return 0;}
static inline int ble_hs_util_ensure_addr(int n){(void)n;return 0;}
static inline int ble_hs_id_infer_auto(int n,uint8_t *t){(void)n;*t=0;return 0;}
static inline QueueHandle_t xQueueCreate(int count,size_t size){(void)count;(void)size;return (void *)1;}
static inline int xQueueSend(QueueHandle_t q,const void *data,int wait){(void)q;(void)data;(void)wait;return pdTRUE;}
static inline int xQueueReceive(QueueHandle_t q,void *data,int wait){(void)q;(void)data;(void)wait;return 0;}
static inline void vQueueDelete(QueueHandle_t q){(void)q;}
static inline int xTaskCreate(void (*f)(void *),const char *name,int stack,void *arg,int priority,void *handle){(void)f;(void)name;(void)stack;(void)arg;(void)priority;(void)handle;return pdPASS;}
static inline void vTaskDelete(void *t){(void)t;}
static inline int nimble_port_init(void){return 0;}
static inline int nimble_port_deinit(void){return 0;}
static inline void nimble_port_run(void){}
static inline void ble_svc_gap_init(void){}
static inline void ble_svc_gatt_init(void){}
static inline int ble_svc_gap_device_name_set(const char *name){(void)name;return 0;}
static inline int ble_gatts_count_cfg(const struct ble_gatt_svc_def *s){(void)s;return 0;}
static inline int ble_gatts_add_svcs(const struct ble_gatt_svc_def *s){(void)s;return 0;}
static inline int ble_hs_mbuf_to_flat(struct os_mbuf *om,void *out,size_t n,void *length){(void)om;(void)out;(void)n;(void)length;return 0;}
static inline struct os_mbuf *ble_hs_mbuf_from_flat(const void *data,size_t n){(void)data;(void)n;static struct os_mbuf m;return &m;}
static inline uint16_t ble_att_mtu(uint16_t h){(void)h;return 247;}
static inline int ble_gatts_notify_custom(uint16_t h,uint16_t a,struct os_mbuf *m){(void)h;(void)a;(void)m;return 0;}
