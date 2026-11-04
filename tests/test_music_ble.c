#include <assert.h>
#include <stdio.h>
#include "../main/music_ble.c"
void ble_store_config_init(void){}

int main(void) {
    assert(music_ble_start()==ESP_OK);
    assert(ble_hs_cfg.sm_bonding && ble_hs_cfg.sm_mitm && ble_hs_cfg.sm_sc);
    assert(ble_hs_cfg.sm_io_cap==BLE_SM_IO_CAP_DISP_ONLY);
    test_desc.peer_id_addr=(ble_addr_t){.type=1,.val={1,2,3,4,5,6}};
    atomic_store(&secure,true);atomic_store(&subscribed,true);
    struct ble_gap_event e={.type=BLE_GAP_EVENT_REPEAT_PAIRING,.repeat_pairing={.conn_handle=42}};
    assert(gap(&e,NULL)==BLE_GAP_REPEAT_PAIRING_RETRY);
    assert(test_looked_up==42 && test_delete_calls==1);
    assert(!memcmp(&test_deleted,&test_desc.peer_id_addr,sizeof(test_deleted)));
    assert(!atomic_load(&secure) && !atomic_load(&subscribed));
    assert(music_ble_passkey()==1000000);
    assert(!music_ble_send("x",1)); // Re-pairing cannot bypass encryption.

    test_lookup_result=1;
    assert(gap(&e,NULL)==BLE_GAP_REPEAT_PAIRING_IGNORE);
    assert(test_delete_calls==1); // Never delete a peer without its identity.
    test_lookup_result=0;test_delete_result=1;
    assert(gap(&e,NULL)==BLE_GAP_REPEAT_PAIRING_IGNORE);
    assert(test_delete_calls==2); // No infinite RETRY when storage fails.

    e=(struct ble_gap_event){.type=BLE_GAP_EVENT_PASSKEY_ACTION,.passkey={.conn_handle=42,.params={.action=BLE_SM_IOACT_DISP}}};
    gap(&e,NULL);assert(music_ble_passkey()==123456);
    e=(struct ble_gap_event){.type=BLE_GAP_EVENT_ENC_CHANGE,.enc_change={.conn_handle=42,.status=0}};
    test_desc.sec_state.encrypted=true;test_desc.sec_state.authenticated=false;
    gap(&e,NULL);assert(!atomic_load(&secure));
    test_desc.sec_state.authenticated=true;
    gap(&e,NULL);assert(atomic_load(&secure));assert(music_ble_passkey()==1000000);
    assert(test_terminate_calls==0);
    e.enc_change.status=7;
    gap(&e,NULL);assert(!atomic_load(&secure));
    assert(test_terminate_calls==1 && test_terminated==42 && test_terminate_reason==BLE_ERR_AUTH_FAIL);
    e=(struct ble_gap_event){.type=BLE_GAP_EVENT_DISCONNECT};
    gap(&e,NULL);assert(test_advertisements==1);
    assert(atomic_load(&connection)==BLE_HS_CONN_HANDLE_NONE && !atomic_load(&subscribed));
    puts("Music BLE: stale peer repair, authenticated access and error recovery PASS");
    return 0;
}
