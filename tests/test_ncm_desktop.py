import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock,MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from ncm_desktop import DesktopPlayer,normalize_snapshot,validate_target,TOGGLE_DESKTOP_LYRICS

class NativeStateTest(unittest.TestCase):
    def state(self,**changes):
        result=dict(title='Test',artist='Artist',album='Album',song_id='123',duration=180000,
                    position=21120,volume=95,playing=True)
        result.update(changes);return result
    def test_real_seek_time_and_internal_volume(self):
        state=normalize_snapshot(self.state())
        self.assertEqual((state['position'],state['duration'],state['volume'],state['song_id']),(21120,180000,95,123))
    def test_native_audio_clock_wins_over_lagging_seek(self):
        state=normalize_snapshot(self.state(audio_position=21710,audio_track='123',audio_age=15))
        self.assertEqual((state['position'],state['clock_source']),(21710,'audio'))
    def test_native_clock_is_scoped_to_track_and_fresh_playback_events(self):
        for changes in (dict(audio_track='other'),dict(audio_age=2000),dict(audio_position=float('nan'))):
            raw=self.state(audio_position=21710,audio_track='123',audio_age=15);raw.update(changes)
            self.assertEqual(normalize_snapshot(raw)['position'],21120)
    def test_paused_audio_clock_stays_fixed_without_extrapolation(self):
        state=normalize_snapshot(self.state(playing=False,audio_position=21710,audio_track='123',audio_age=60000))
        self.assertEqual(state['position'],21710)
    def test_native_zero_position_without_visible_slider_is_valid(self):
        state=normalize_snapshot(self.state(position=None,audio_position=0,audio_track='123',audio_age=15))
        self.assertEqual((state['position'],state['duration']),(0,180000))
    def test_missing_seek_never_creates_a_fake_clock(self):
        state=normalize_snapshot(self.state(position=None))
        self.assertEqual((state['position'],state['duration']),(0,0))
    def test_binary_float_does_not_lose_one_volume_point(self):
        self.assertEqual(normalize_snapshot(self.state(volume=94.99999999999997))['volume'],95)
    def test_invalid_numbers_fail_closed(self):
        for field,value in [('volume',101),('volume',float('nan')),('position',-1),('duration','180')]:
            with self.assertRaises(ValueError):normalize_snapshot(self.state(**{field:value}))
    def test_desktop_lyrics_reports_native_boolean_without_guessing(self):
        for value,expected in [(True,1),(False,0),(None,-1),('false',-1),(1,-1)]:
            self.assertEqual(normalize_snapshot(self.state(desktop_lyrics=value))['desktop_lyrics'],expected)
    def test_non_numeric_track_id_is_not_sent_to_lyrics_endpoint(self):
        self.assertIsNone(normalize_snapshot(self.state(song_id='local:file'))['song_id'])

class TargetTest(unittest.TestCase):
    def target(self,url):
        return [dict(type='page',url='orpheus://orpheus/pub/app.html',webSocketDebuggerUrl=url)]
    def test_local_verified_player(self):
        url='ws://127.0.0.1:9223/devtools/page/test'
        self.assertEqual(validate_target({'User-Agent':'NeteaseMusicDesktop/3.1.31'},self.target(url),9223),url)
    def test_foreign_apps_remote_hosts_and_credentials_rejected(self):
        version={'User-Agent':'NeteaseMusicDesktop/3.1.31'}
        for url in ['ws://example.com:9223/test','ws://127.0.0.1:8000/test','ws://user@127.0.0.1:9223/test']:
            with self.assertRaises(RuntimeError):validate_target(version,self.target(url),9223)
        with self.assertRaises(RuntimeError):validate_target({'User-Agent':'OtherApp'},self.target('ws://127.0.0.1:9223/test'),9223)
    def test_discovery_uses_plain_loopback_http_not_default_ssl_opener(self):
        version={'User-Agent':'NeteaseMusicDesktop/3.1.31'}
        url='ws://127.0.0.1:9223/devtools/page/test'
        reply=MagicMock();reply.status=200
        reply.read.side_effect=[json.dumps(version).encode(),json.dumps(self.target(url)).encode()]
        conn=MagicMock();conn.getresponse.return_value=reply
        with patch('ncm_desktop.HTTPConnection',return_value=conn) as factory:
            self.assertEqual(DesktopPlayer().discover(),url)
        self.assertEqual(factory.call_count,2)
        factory.assert_called_with('127.0.0.1',9223,timeout=2)

class ProtocolTest(unittest.IsolatedAsyncioTestCase):
    async def test_double_volume_is_one_native_dispatch(self):
        player=DesktopPlayer();player.evaluate=AsyncMock(return_value=dict(before=50,after=70))
        for action,step in (('volume_up_20',.2),('volume_down_20',-.2),('volume_up',.05),('volume_down',-.05)):
            player.evaluate.reset_mock()
            await player.command(action)
            player.evaluate.assert_awaited_once()
            expression=player.evaluate.call_args.args[0]
            self.assertIn('before+'+str(step),expression)
            self.assertEqual(expression.count("s.dispatch({type:'playing/setVolume'"),1)
    async def test_desktop_lyrics_uses_native_effect_and_validates_transition(self):
        player=DesktopPlayer();player.evaluate=AsyncMock(return_value=dict(before=False,after=True))
        self.assertEqual(await player.command('toggle_desktop_lyrics'),dict(before=False,after=True))
        player.evaluate.assert_awaited_once_with(TOGGLE_DESKTOP_LYRICS)
        for result in (None,True,dict(before=False,after=False),dict(before=0,after=True)):
            player.evaluate=AsyncMock(return_value=result)
            with self.assertRaises(RuntimeError):await player.command('toggle_desktop_lyrics')
    async def test_legacy_cef_uses_request_liveness_without_control_pings(self):
        import types
        socket=MagicMock();connection=AsyncMock(return_value=socket)
        player=DesktopPlayer();player.discover=MagicMock(return_value='ws://127.0.0.1:9223/test')
        player.evaluate=AsyncMock(return_value=True)
        modules={'websockets':types.SimpleNamespace(),'websockets.asyncio':types.SimpleNamespace(),
                 'websockets.asyncio.client':types.SimpleNamespace(connect=connection)}
        with patch.dict(sys.modules,modules):await player.connect()
        self.assertIsNone(connection.call_args.kwargs['ping_interval'])
        self.assertEqual(connection.call_args.kwargs['open_timeout'],3)

    async def test_notifications_do_not_get_mistaken_for_command_replies(self):
        player=DesktopPlayer();player.socket=MagicMock();player.socket.send=AsyncMock()
        player.socket.recv=AsyncMock(side_effect=[json.dumps({'method':'Runtime.consoleAPICalled'}),
            json.dumps({'id':1,'result':{'result':{'value':95}}})])
        self.assertEqual(await player.evaluate('test'),95)
    async def test_runtime_errors_are_not_reported_as_success(self):
        player=DesktopPlayer();player.socket=MagicMock();player.socket.send=AsyncMock()
        player.socket.recv=AsyncMock(return_value=json.dumps({'id':1,'result':{'exceptionDetails':{'text':'error'}}}))
        with self.assertRaises(RuntimeError):await player.evaluate('test')
    async def test_device_cannot_supply_an_arbitrary_native_command(self):
        player=DesktopPlayer()
        with self.assertRaises(ValueError):await player.command('arbitrary_js')

if __name__=='__main__':unittest.main()
