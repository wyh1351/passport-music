import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'companion'))
from music_core import CommandDecoder, PREFIX, frame, parse_lrc, lyric_window, find_song, load_lyrics, safe_name, http_json
from passport_music import Bridge, DemoMusic, ble_run, ble_connection_parameters

class ConnectionParametersTest(unittest.IsolatedAsyncioTestCase):
    async def check_preference(self,unavailable=False):
        import types
        from unittest.mock import AsyncMock,MagicMock
        device=MagicMock();request=MagicMock();request.status=1
        device.request_preferred_connection_parameters.side_effect=OSError('unsupported') if unavailable else None
        device.request_preferred_connection_parameters.return_value=request
        module=types.SimpleNamespace(BluetoothLEDevice=types.SimpleNamespace(from_bluetooth_address_async=AsyncMock(return_value=device)),BluetoothLEPreferredConnectionParameters=types.SimpleNamespace(throughput_optimized='fast'))
        class StopTest(Exception):pass
        with patch.dict(sys.modules,{'winrt.windows.devices.bluetooth':module}),patch.object(sys,'platform','win32'):
            with self.assertRaises(StopTest):
                async with ble_connection_parameters('11:22:33:44:55:66'):raise StopTest
        device.close.assert_called_once()
        if unavailable:request.close.assert_not_called()
        else:request.close.assert_called_once()
    async def test_preference_is_released_on_disconnection(self):
        await self.check_preference()
    async def test_older_windows_keeps_default_connection_parameters(self):
        await self.check_preference(True)

class WindowsPairingTest(unittest.IsolatedAsyncioTestCase):
    async def check_pairing(self, paired):
        import types
        from unittest.mock import AsyncMock, MagicMock
        from music_core import SERVICE
        native=MagicMock();native.device_information.id='test-device'
        native_type=types.SimpleNamespace(from_bluetooth_address_async=AsyncMock(return_value=native))
        info=types.SimpleNamespace(pairing=types.SimpleNamespace(is_paired=paired))
        info_type=types.SimpleNamespace(create_from_id_async=AsyncMock(return_value=info))
        device=types.SimpleNamespace(address='11:22:33:44:55:66')
        adv=types.SimpleNamespace(service_uuids=[SERVICE])
        scanner=types.SimpleNamespace(discover=AsyncMock(return_value={'device':(device,adv)}))
        client=MagicMock();client.__aenter__.return_value=client;client.__aexit__.return_value=False
        client.start_notify=AsyncMock()
        constructor=MagicMock(return_value=client)
        bridge=types.SimpleNamespace(received=MagicMock(),run=AsyncMock())
        modules={
            'bleak':types.SimpleNamespace(BleakClient=constructor,BleakScanner=scanner),
            'winrt.windows.devices.bluetooth':types.SimpleNamespace(BluetoothLEDevice=native_type),
            'winrt.windows.devices.enumeration':types.SimpleNamespace(DeviceInformation=info_type)}
        with patch.dict(sys.modules,modules),patch.object(sys,'platform','win32'):
            if paired:
                await ble_run(bridge,types.SimpleNamespace(address=None))
                constructor.assert_called_once_with(device,pair=False,timeout=60)
                bridge.run.assert_awaited_once()
            else:
                with self.assertRaisesRegex(RuntimeError,'Windows 设置'):
                    await ble_run(bridge,types.SimpleNamespace(address=None))
                constructor.assert_not_called()
        native.close.assert_called_once()

    async def test_unpaired_device_requires_windows_passkey_pairing(self):
        await self.check_pairing(False)

    async def test_bonded_device_never_uses_pinless_auto_pairing(self):
        await self.check_pairing(True)

class ProtocolTest(unittest.TestCase):
    def test_large_volume_commands_are_fragment_safe_and_not_replayed(self):
        for action in ('volume_up_20','volume_down_20'):
            packet=PREFIX+json.dumps(dict(type='command',boot=11,id=1,action=action)).encode()+b'\n'
            for size in range(1,len(packet)+1):
                decoder=CommandDecoder();commands=[]
                for offset in range(0,len(packet),size):commands.extend(decoder.feed(packet[offset:offset+size]))
                self.assertEqual(commands,[action]);self.assertEqual(decoder.feed(packet),[])
    def test_desktop_lyrics_toggle_is_allowed_once_per_command(self):
        packet=PREFIX+b'{"type":"command","boot":1,"id":5,"action":"toggle_desktop_lyrics"}\n'
        decoder=CommandDecoder()
        self.assertEqual(decoder.feed(packet[:30]),[])
        self.assertEqual(decoder.feed(packet[30:]),['toggle_desktop_lyrics'])
        self.assertEqual(decoder.feed(packet),[])
    def test_device_settings_are_absolute_idempotent_and_fragment_safe(self):
        packet=PREFIX+b'{"type":"settings","boot":10,"lyric_offset_ms":-150}\n'
        for size in range(1,len(packet)+1):
            decoder=CommandDecoder()
            for start in range(0,len(packet),size):self.assertEqual(decoder.feed(packet[start:start+size]),[])
            self.assertEqual(decoder.offset_ms,-150)
            self.assertEqual(decoder.feed(packet),[])
            self.assertEqual(decoder.offset_ms,-150)
    def test_invalid_settings_never_replace_last_valid_value(self):
        decoder=CommandDecoder()
        decoder.feed(PREFIX+b'{"type":"settings","boot":1,"lyric_offset_ms":100}\n')
        for value in (True,2001,-2050,25,'50',None):
            decoder.feed(PREFIX+json.dumps(dict(type='settings',boot=1,lyric_offset_ms=value)).encode()+b'\n')
            self.assertEqual(decoder.offset_ms,100)
        self.assertEqual(decoder.feed(PREFIX+b'{"type":"command","boot":1,"id":5,"action":"toggle"}\n'),['toggle'])
        decoder.feed(PREFIX+b'{"type":"settings","boot":1,"lyric_offset_ms":150}\n')
        self.assertEqual(decoder.feed(PREFIX+b'{"type":"command","boot":1,"id":5,"action":"toggle"}\n'),[])
    def test_board_restart_without_usb_reenumeration(self):
        d=CommandDecoder()
        def packet(boot,ident):
            return PREFIX+json.dumps(dict(type='command',boot=boot,id=ident,action='toggle')).encode()+b'\n'
        self.assertEqual(d.feed(packet(10,50)),['toggle'])
        self.assertEqual(d.feed(packet(10,50)),[])
        self.assertEqual(d.feed(packet(11,1)),['toggle'])
        self.assertEqual(d.feed(packet(11,1)),[])

    def test_every_ble_fragment_size_and_duplicate(self):
        packet=PREFIX+b'{"type":"command","id":1,"action":"next"}\n'
        for n in range(1,len(packet)+1):
            d=CommandDecoder(); commands=[]
            for i in range(0,len(packet),n): commands.extend(d.feed(packet[i:i+n]))
            self.assertEqual(commands,['next']); self.assertEqual(d.feed(packet),[])

    def test_noise_invalid_and_resync(self):
        d=CommandDecoder()
        invalid=[b'x'*1000+b'\n', PREFIX+b'[]\n', PREFIX+b'null\n',
                 PREFIX+b'{"type":"command","id":true,"action":"next"}\n',
                 PREFIX+b'{"type":"command","id":2,"action":"shell"}\n']
        for item in invalid: self.assertEqual(d.feed(item),[])
        self.assertEqual(d.feed(PREFIX+b'{"type":"command","id":3,"action":"toggle"}\n'),['toggle'])

    def test_frame_bounded_unicode(self):
        packet=frame(dict(title='中'*200,lyric='歌'*1000,position=0,duration=0,volume=50,playing=True,available=True))
        self.assertLess(len(packet),4096)
        state=json.loads(packet[len(PREFIX):]); self.assertEqual(len(state['title'].encode()),192)
        self.assertEqual(len(state['lyric'].encode()),384)

class LyricsTest(unittest.TestCase):
    def test_native_http_direct_ignores_stale_proxy_and_machine_defaults(self):
        import types
        from unittest.mock import MagicMock
        native=types.SimpleNamespace(COMError=type('NativeError',(Exception,),{}),CoInitialize=MagicMock(),CoUninitialize=MagicMock())
        request=MagicMock();request.Status=200;request.ResponseText='{}'
        client=types.SimpleNamespace(CreateObject=MagicMock(return_value=request))
        for proxies in ({},{'https':'http://127.0.0.1:8888'}, {'https':'socks5://127.0.0.1:8888'}):
            request.reset_mock()
            with patch.dict(sys.modules,{'comtypes':native,'comtypes.client':client}),patch.object(sys,'platform','win32'),patch('music_core.getproxies',return_value=proxies) as lookup:
                self.assertEqual(http_json('https://music.163.com/test'),{})
            request.SetProxy.assert_called_once_with(1)
            lookup.assert_not_called()

    def test_native_http_proxy_fallback_and_fresh_settings_after_disconnect(self):
        import types
        from unittest.mock import MagicMock,call
        class NativeError(Exception):pass
        native=types.SimpleNamespace(COMError=NativeError,CoInitialize=MagicMock(),CoUninitialize=MagicMock())
        direct=MagicMock();direct.Send.side_effect=NativeError('direct unavailable')
        proxied=MagicMock();proxied.Status=200;proxied.ResponseText='{"code":200}'
        client=types.SimpleNamespace(CreateObject=MagicMock(side_effect=[direct,proxied,direct]))
        with patch.dict(sys.modules,{'comtypes':native,'comtypes.client':client}),patch.object(sys,'platform','win32'),patch('music_core.getproxies',side_effect=[{'https':'http://user:pass@127.0.0.1:8888'},{}]) as lookup,patch('music_core.proxy_bypass',return_value=False):
            payload=b's=Test&type=1'
            self.assertEqual(http_json('https://music.163.com/api/search/get',payload),{'code':200})
            # A later failure with proxy disabled must not reuse the old route.
            with self.assertRaises(OSError):http_json('https://music.163.com/test')
        self.assertEqual(direct.SetProxy.call_args_list,[call(1),call(1)])
        proxied.SetProxy.assert_called_once_with(2,'127.0.0.1:8888')
        proxied.SetCredentials.assert_called_once_with('user','pass',1)
        proxied.Send.assert_called_once_with(payload.decode('ascii'))
        self.assertEqual(lookup.call_count,2)
        self.assertEqual(native.CoInitialize.call_count,3)
        self.assertEqual(native.CoUninitialize.call_count,3)

    def test_failed_direct_respects_proxy_bypass_and_bounded_failure(self):
        from unittest.mock import call
        for proxies,bypass,attempts in (({},False,1),({'https':'http://localhost:8888'},True,1),({'https':'http://localhost:8888'},False,2)):
            with patch('music_core._http_json_once',side_effect=OSError('offline')) as request,patch('music_core.getproxies',return_value=proxies),patch('music_core.proxy_bypass',return_value=bypass):
                with self.assertRaises(OSError):http_json('https://music.163.com/test')
            self.assertEqual(request.call_count,attempts)
            if attempts==2:self.assertEqual(request.call_args,call('https://music.163.com/test',None,'http://localhost:8888'))

    def test_portable_http_also_explicitly_disables_proxy_for_direct(self):
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{}'
        opener=MagicMock();opener.open.return_value=response
        with patch.object(sys,'platform','linux'),patch('music_core.build_opener',return_value=opener) as build,patch('music_core.getproxies') as lookup:
            self.assertEqual(http_json('https://music.163.com/test'),{})
        self.assertEqual(build.call_args.args[0].proxies,{})
        lookup.assert_not_called()

    def test_native_http_timeout_becomes_retryable_transport_error(self):
        import types
        from unittest.mock import MagicMock
        class NativeError(Exception):pass
        native=types.SimpleNamespace(COMError=NativeError,CoInitialize=MagicMock(),CoUninitialize=MagicMock())
        client=types.SimpleNamespace(CreateObject=MagicMock(side_effect=NativeError('timeout')))
        with patch.dict(sys.modules,{'comtypes':native,'comtypes.client':client}),patch.object(sys,'platform','win32'),patch('music_core.getproxies',return_value={}):
            with self.assertRaises(OSError):http_json('https://music.163.com/test')
        native.CoUninitialize.assert_called_once()

    def test_internal_song_id_bypasses_ambiguous_name_search(self):
        with tempfile.TemporaryDirectory() as directory,patch('music_core.http_json',return_value={'lrc':{'lyric':'[00:01]测试歌词'}}) as request:
            lines,message=load_lyrics('Test','Artist',180000,directory,song_id=123)
        self.assertEqual(lines,[(1000,'测试歌词')]);self.assertEqual(request.call_count,1)
        self.assertIn('id=123',request.call_args.args[0]);self.assertIn('在线',message)

    def test_duplicate_albums_without_timeline_can_supply_manual_lyrics(self):
        song=dict(id=1,name='Test',artists=[{'name':'Artist'}],duration=180000)
        data={'result':{'songs':[song,dict(song,id=2,duration=181000)]}}
        with tempfile.TemporaryDirectory() as directory,patch('music_core.http_json',side_effect=[data,{'lrc':{'lyric':'[00:01]测试歌词'}}]):
            lines,message=load_lyrics('Test','Artist',0,directory)
        self.assertEqual(lines,[(1000,'测试歌词')]);self.assertIn('手动',message)

    def test_distinct_length_versions_are_not_used_as_manual_fallback(self):
        song=dict(id=1,name='Test',artists=[{'name':'Artist'}],duration=180000)
        data={'result':{'songs':[song,dict(song,id=2,duration=240000)]}}
        with tempfile.TemporaryDirectory() as directory,patch('music_core.http_json',return_value=data) as request:
            lines,message=load_lyrics('Test','Artist',0,directory)
        self.assertEqual(lines,[]);self.assertIn('未匹配',message);self.assertEqual(request.call_count,1)

    def test_multi_stamp_offset_and_boundaries(self):
        lines=parse_lrc('[offset:-100]\n[00:01.20][00:03.123]中文\n[00:05]下一句\n[ar:test]')
        self.assertEqual(lines,[(1100,'中文'),(3023,'中文'),(4900,'下一句')])
        self.assertEqual(lyric_window(lines,1099),('','','中文'))
        self.assertEqual(lyric_window(lines,3023),('中文','中文','下一句'))
        self.assertEqual(lyric_window(lines,5000),('中文','下一句',''))

    def test_strict_matching(self):
        song=dict(id=1,name='Test',artists=[{'name':'Artist'}],duration=180000)
        self.assertEqual(find_song([song],'Test','Artist',180000),1)
        self.assertIsNone(find_song([song],'Test (Live)','Artist',180000))
        self.assertIsNone(find_song([song],'Test','Other',180000))
        self.assertIsNone(find_song([song,dict(song,id=2)],'Test','Artist',180000))
        self.assertIsNone(find_song([song],'Test','Artist',190000))

    def test_local_and_network_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/(safe_name('标题','歌手')+'.lrc')
            path.write_text('[00:01]本地歌词',encoding='utf-8-sig')
            self.assertEqual(load_lyrics('标题','歌手',1,directory,False)[0],[(1000,'本地歌词')])
            with patch('music_core.http_json',side_effect=OSError):
                self.assertEqual(load_lyrics('other','artist',1,directory)[0],[])

class BridgeTest(unittest.IsolatedAsyncioTestCase):
    async def run_snapshots(self,snapshots,lookup,lead_ms=0,manual_ms=0):
        import argparse
        from unittest.mock import AsyncMock
        provider=type('Provider',(),{})()
        provider.snapshot=AsyncMock(side_effect=snapshots)
        bridge=Bridge(provider,argparse.Namespace(demo=False,lyrics='.',offline=False));states=[]
        bridge.lyric_lead_ms=lead_ms
        bridge.manual_offset_ms=manual_ms
        class StopRun(Exception):pass
        async def send(packet):
            states.append(json.loads(packet[len(PREFIX):]))
            if len(states)==len(snapshots):raise StopRun
        with patch('passport_music.load_lyrics',side_effect=lookup) as request:
            with self.assertRaises(StopRun):await bridge.run(send)
        return states,request.call_count

    async def test_manual_offset_adds_to_automatic_without_changing_progress(self):
        base=dict(title='Test',artist='Artist',album='',position=900,duration=180000,volume=50,playing=True,available=True,song_id=123,clock_source='audio')
        for manual,expected in ((200,'第二句'),(-500,'第一句')):
            states,_=await self.run_snapshots([base,base],[([(0,'第一句'),(1000,'第二句')],'在线歌词')],200,manual)
            self.assertEqual(states[-1]['lyric'],expected)
            self.assertEqual(states[-1]['position'],900)
            self.assertEqual(states[-1]['lyric_offset_ack'],manual)

    def test_device_settings_apply_before_player_is_available(self):
        import argparse
        bridge=Bridge(DemoMusic(),argparse.Namespace())
        bridge.received(PREFIX+b'{"type":"settings","boot":1,"lyric_offset_ms":-100}\n')
        self.assertEqual(bridge.manual_offset_ms,-100)
        self.assertTrue(bridge.commands.empty())

    async def test_delivery_compensation_changes_only_playing_lyric_selection(self):
        base=dict(title='Test',artist='Artist',album='',position=900,duration=180000,volume=50,playing=True,available=True,song_id=123,clock_source='audio')
        states,_=await self.run_snapshots([base,base],[([(0,'第一句'),(1000,'第二句')],'在线歌词')],400)
        self.assertEqual(states[-1]['lyric'],'第二句')
        self.assertEqual(states[-1]['position'],900)
        self.assertEqual(states[-1]['duration'],180000)

    async def test_paused_or_fallback_clock_never_advances_lyrics(self):
        base=dict(title='Test',artist='Artist',album='',position=900,duration=180000,volume=50,playing=True,available=True,song_id=123,clock_source='audio')
        for changes in (dict(playing=False),dict(clock_source='seek')):
            state=dict(base,**changes)
            states,_=await self.run_snapshots([state,state],[([(0,'第一句'),(1000,'第二句')],'在线歌词')],400)
            self.assertEqual(states[-1]['lyric'],'第一句')
            self.assertEqual(states[-1]['position'],900)

    def test_delivery_estimate_is_bounded_and_ignores_transport_stalls(self):
        import argparse
        bridge=Bridge(DemoMusic(),argparse.Namespace())
        bridge.observe_delivery(.3)
        self.assertEqual(bridge.lyric_lead_ms,400)
        bridge.observe_delivery(.9)
        self.assertLessEqual(bridge.lyric_lead_ms,600)
        previous=bridge.lyric_lead_ms
        for value in (2,float('nan'),-1,None):bridge.observe_delivery(value)
        self.assertEqual(bridge.lyric_lead_ms,previous)

    async def test_same_id_metadata_and_temporary_fallback_never_reload_lyrics(self):
        base=dict(title='Test',artist='Artist',album='Album',position=2000,duration=180000,volume=50,playing=True,available=True,song_id=123)
        snapshots=[base,dict(base,duration=0),dict(base,duration=180001,album=''),dict(base,song_id=None,duration=0),base]
        states,count=await self.run_snapshots(snapshots,[([(0,'当前歌词')],'在线歌词')])
        self.assertEqual(count,1)
        self.assertTrue(all(s['lyric']=='当前歌词' for s in states[1:]))

    async def test_returning_to_cached_song_does_not_show_search_status(self):
        base=dict(title='Test',artist='Artist',album='Album',position=2000,duration=180000,volume=50,playing=True,available=True,song_id=1)
        other=dict(base,title='Other',song_id=2)
        states,count=await self.run_snapshots([base,base,other,other,base],[([(0,'第一首')],'在线歌词'), ([(0,'第二首')],'在线歌词')])
        self.assertEqual(count,2)
        self.assertEqual(states[2]['lyric'],'')
        self.assertEqual(states[4]['lyric'],'第一首')
        self.assertEqual(states[4]['message'],'在线歌词')

    async def test_transient_lyric_error_retries_for_unchanged_song(self):
        import argparse
        bridge=Bridge(DemoMusic(),argparse.Namespace(demo=False,lyrics='.',offline=False))
        states=[]
        class StopRun(Exception): pass
        async def send(packet):
            states.append(json.loads(packet[len(PREFIX):]))
            if len(states)==2: bridge.lyric_retry_at=1
            if len(states)==4: raise StopRun
        with patch('passport_music.load_lyrics',side_effect=[([], '歌词查询失败，稍后自动重试'), ([(0,'恢复歌词')],'在线歌词')]) as lookup:
            with self.assertRaises(StopRun): await bridge.run(send)
        self.assertEqual(lookup.call_count,2);self.assertEqual(states[3]['lyric'],'恢复歌词')

    async def test_manual_lyrics_without_timeline(self):
        import argparse
        provider=DemoMusic()
        original=provider.snapshot
        async def snapshot():
            result=await original(); result['duration']=0; return result
        provider.snapshot=snapshot
        bridge=Bridge(provider,argparse.Namespace(demo=True,lyrics='.',offline=True))
        states=[]
        class StopRun(Exception): pass
        async def send(packet):
            states.append(json.loads(packet[len(PREFIX):]))
            if len(states)==2:
                bridge.received(PREFIX+b'{"type":"command","id":1,"action":"lyric_next"}\n')
            if len(states)==3: raise StopRun
        with self.assertRaises(StopRun): await bridge.run(send)
        self.assertEqual(states[2]['lyric'],'上键和下键调整音量')
        self.assertEqual(states[2]['before'],'蓝牙连接测试')

    async def test_snapshot_controls_and_lyrics_without_hardware(self):
        import argparse
        provider=DemoMusic(); await provider.initialize()
        args=argparse.Namespace(demo=True,lyrics='.',offline=True)
        bridge=Bridge(provider,args); states=[]
        class StopRun(Exception): pass
        async def send(packet):
            states.append(json.loads(packet[len(PREFIX):]))
            if len(states)==1:
                bridge.received(PREFIX+b'{"type":"command","id":1,"action":"volume_up"}\n')
            if len(states)==3: raise StopRun
        with self.assertRaises(StopRun): await bridge.run(send)
        self.assertEqual(provider.volume,55)
        self.assertEqual(states[2]['volume'],55)
        self.assertEqual(states[2]['lyric'],'蓝牙连接测试')

if __name__=='__main__': unittest.main()
