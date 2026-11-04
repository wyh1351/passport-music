"""Passport Music bridge for Windows 10 1809+/11. BLE first; USB optional."""
import argparse
import asyncio
from collections import OrderedDict
from contextlib import contextmanager,asynccontextmanager
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import sys
import time

# comtypes must not initialize STA before Bleak/WinRT's asyncio MTA operations.
sys.coinit_flags = 0
from music_core import (SERVICE, RX, TX, CommandDecoder, frame, load_lyrics, lyric_window)
from ncm_desktop import VOLUME_STEPS

class WindowsMediaSession:
    def __init__(self):
        self.manager = None
        self.session = None

    async def initialize(self):
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        self.manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()

    async def snapshot(self):
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
        sessions = [s for s in self.manager.get_sessions()
                    if any(token in s.source_app_user_model_id.casefold() for token in ("cloudmusic", "netease"))]
        self.session = next((s for s in sessions if s.get_playback_info().playback_status == Status.PLAYING),
                            sessions[0] if sessions else None)
        if self.session is None:
            return dict(title="请打开网易云音乐", artist="并播放一首歌曲", album="", position=0,
                        duration=0, volume=-1, playing=False, available=False)
        props = await asyncio.wait_for(self.session.try_get_media_properties_async(), 3)
        timeline = self.session.get_timeline_properties()
        playing = self.session.get_playback_info().playback_status == Status.PLAYING
        position = max(0, int((timeline.position-timeline.start_time).total_seconds()*1000))
        duration = max(0, int((timeline.end_time-timeline.start_time).total_seconds()*1000))
        if playing:
            elapsed = (datetime.now(timezone.utc)-timeline.last_updated_time).total_seconds()
            if 0 <= elapsed < 86400: position += int(elapsed*1000)
        if duration: position = min(position, duration)
        volume = -1
        return dict(title=props.title or "未知歌曲", artist=props.artist or "未知歌手", album=props.album_title or "",
                    position=position, duration=duration, volume=volume, playing=playing, available=True)

    async def command(self, action):
        if not self.session: return "网易云未就绪"
        if action in VOLUME_STEPS or action=='toggle_desktop_lyrics':
            return "请用遥控启动器打开网易云"
        method = {"next": "try_skip_next_async", "previous": "try_skip_previous_async",
                  "toggle": "try_toggle_play_pause_async"}.get(action)
        if not method: return "未知操作"
        success = await asyncio.wait_for(getattr(self.session, method)(), 3)
        return "操作成功" if success else "网易云未接受操作"

class WindowsMusic:
    """Prefer the real internal player; SMTC is a limited compatibility fallback."""
    def __init__(self,port=9223):
        from ncm_desktop import DesktopPlayer
        self.desktop=DesktopPlayer(port);self.media=WindowsMediaSession()
        self.native=False

    async def initialize(self):
        try: await self.media.initialize()
        except OSError: pass

    async def snapshot(self):
        try:
            state=await self.desktop.snapshot();self.native=True;return state
        except Exception as exc:
            logging.getLogger(__name__).info('Internal snapshot fallback: %s',type(exc).__name__)
            self.native=False
            if self.media.manager:
                return await self.media.snapshot()
            return dict(title="请用遥控启动器打开网易云",artist="",album="",position=0,duration=0,
                        volume=-1,playing=False,available=False)

    async def command(self,action):
        if self.native:
            try:
                result=await self.desktop.command(action)
                if action in VOLUME_STEPS:
                    logging.getLogger(__name__).info('Internal volume command %s: %s',action,result)
                    return f"网易云内部音量 {result['after']}%"
                if action=='toggle_desktop_lyrics':
                    return "桌面歌词已开启" if result['after'] else "桌面歌词已关闭"
                logging.getLogger(__name__).info('Player command accepted: %s',action)
                return "操作成功"
            except Exception:
                await self.desktop.close();self.native=False
                return "内部接口已断开，正在重连"
        return await self.media.command(action)

class DemoMusic:
    """Deterministic simulator. It never controls a real media session."""
    def __init__(self): self.position=0; self.volume=50; self.playing=True; self.track=1; self.desktop_lyrics=False
    async def initialize(self): pass
    async def snapshot(self):
        self.position += 500 if self.playing else 0
        return dict(title=f"连接测试 {self.track}", artist="模拟模式", album="不控制真实播放器", position=self.position,
                    duration=180000, volume=self.volume, playing=self.playing, available=True,desktop_lyrics=int(self.desktop_lyrics))
    async def command(self, action):
        if action in VOLUME_STEPS: self.volume=max(0,min(100,self.volume+round(VOLUME_STEPS[action]*100)))
        elif action == "toggle": self.playing=not self.playing
        elif action == "toggle_desktop_lyrics": self.desktop_lyrics=not self.desktop_lyrics
        else: self.track+=1; self.position=0
        return "模拟操作成功"

class Bridge:
    def __init__(self, provider, args):
        self.provider=provider; self.args=args; self.commands=asyncio.Queue(maxsize=32)
        self.decoder=CommandDecoder(); self.key=None; self.lyrics=[]; self.lyric_task=None
        self.message="等待歌曲信息"; self.notice=""; self.notice_until=0
        self.manual_index=0
        self.lyric_retry_at=0
        self.lyric_cache=OrderedDict()
        self.details=None
        self.delivery_ms=None
        self.lyric_lead_ms=0
        self.manual_offset_ms=0

    def observe_delivery(self,seconds):
        # Ignore stalls; one congested write must not advance lyrics by seconds.
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=1:return
        measured=seconds*1000
        self.delivery_ms=measured if self.delivery_ms is None else .75*self.delivery_ms+.25*measured
        # Firmware renders every 200ms: use its mean scheduling wait, not a
        # fixed lyric-row offset. Only lyric selection is compensated.
        self.lyric_lead_ms=min(600,round(self.delivery_ms+100))

    def received(self, data):
        for action in self.decoder.feed(data):
            try: self.commands.put_nowait(action)
            except asyncio.QueueFull: pass
        if self.decoder.offset_ms is not None and self.decoder.offset_ms!=self.manual_offset_ms:
            self.manual_offset_ms=self.decoder.offset_ms
            self.notice=f'歌词微调 {self.manual_offset_ms:+d}ms';self.notice_until=time.monotonic()+2

    async def update_lyrics(self, key, details):
        if self.args.demo:
            lines, message = [(0,"蓝牙连接测试"),(4000,"上键和下键调整音量"),(8000,"长按按键切换歌曲")], "模拟歌词"
        else:
            title, artist, duration, album, song_id=details
            lines, message = await asyncio.to_thread(load_lyrics, title, artist, duration,
                self.args.lyrics, not self.args.offline, album, song_id)
        if self.key == key:
            self.lyrics=lines; self.message=message
            if lines:
                self.lyric_cache[key]=(lines,message)
                self.lyric_cache.move_to_end(key)
                while len(self.lyric_cache)>16:self.lyric_cache.popitem(last=False)
            self.lyric_retry_at=time.monotonic()+30 if message.startswith('歌词查询失败') else 0

    async def run(self, send, read=None):
        self.decoder=CommandDecoder()
        while not self.commands.empty(): self.commands.get_nowait()
        while True:
            started=time.monotonic()
            if read:
                data = await read()
                self.received(data)
            # Refresh first: a command must never use a stale session from an
            # earlier snapshot after the player exits or changes session.
            state = await self.provider.snapshot()
            controlled=False
            for _ in range(8):
                try: action=self.commands.get_nowait()
                except asyncio.QueueEmpty: break
                if state["available"]:
                    if action in ('lyric_previous','lyric_next'):
                        if not state['duration']:
                            self.manual_index=max(0,min(len(self.lyrics)-1,self.manual_index+(1 if action=='lyric_next' else -1)))
                    else:
                        self.notice=await self.provider.command(action); self.notice_until=time.monotonic()+2
                        controlled=True
            if controlled:state=await self.provider.snapshot()
            details=(state["title"],state["artist"],state["duration"],state["album"],state.get('song_id'))
            ident=state.get('song_id')
            key=("id",ident) if type(ident) is int and ident>0 else ("metadata",*details[:4])
            # A real song ID owns lyric identity. UI/timeline metadata may settle
            # independently; a temporary SMTC fallback must not discard its lyrics.
            if ident is None and self.key and self.key[0]=='id' and self.details and details[:2]==self.details[:2]:key=self.key
            if not state["available"]:key=None
            if key != self.key:
                self.key=key; self.lyrics=[]; self.manual_index=0
                self.details=details
                self.lyric_retry_at=0
                self.message="正在查找歌词" if key else "启用客户端系统媒体控制"
                if self.lyric_task: self.lyric_task.cancel()
                if key in self.lyric_cache:
                    self.lyrics,self.message=self.lyric_cache[key]
                    self.lyric_cache.move_to_end(key)
                elif key:self.lyric_task=asyncio.create_task(self.update_lyrics(key,details))
            elif key and self.lyric_retry_at and time.monotonic()>=self.lyric_retry_at and (not self.lyric_task or self.lyric_task.done()):
                self.lyric_retry_at=0
                self.lyric_task=asyncio.create_task(self.update_lyrics(key,details))
            lyric_position=state['position']+self.manual_offset_ms
            if state['playing'] and state['duration'] and state.get('clock_source')=='audio':
                lyric_position=min(state['duration'],lyric_position+self.lyric_lead_ms)
            before, current, after=lyric_window(self.lyrics,lyric_position)
            if not state['duration'] and self.lyrics:
                def line(i): return self.lyrics[i][1] if 0<=i<len(self.lyrics) else ''
                before,current,after=line(self.manual_index-1),line(self.manual_index),line(self.manual_index+1)
            state.update(before=before, lyric=current, after=after,lyric_offset_ack=self.manual_offset_ms,
                         message=self.notice if time.monotonic()<self.notice_until else self.message)
            await send(frame(state))
            # Account for actual GATT transmission time instead of adding a
            # fixed half-second delay after every frame. Never queue stale frames.
            await asyncio.sleep(max(0,.2-(time.monotonic()-started)))

@asynccontextmanager
async def ble_connection_parameters(address):
    """Scope Windows 11 throughput preference to this active remote connection."""
    device=request=None
    if sys.platform=='win32':
        try:
            from winrt.windows.devices.bluetooth import BluetoothLEDevice,BluetoothLEPreferredConnectionParameters
            device=await BluetoothLEDevice.from_bluetooth_address_async(int(address.replace(':','').replace('-',''),16))
            if device:
                request=device.request_preferred_connection_parameters(BluetoothLEPreferredConnectionParameters.throughput_optimized)
                logging.getLogger(__name__).info('BLE throughput preference status: %s',request.status)
        except (ImportError,AttributeError,OSError) as exc:
            logging.getLogger(__name__).info('BLE default parameters: %s',type(exc).__name__)
    try:yield
    finally:
        try:
            if request:request.close()
        finally:
            if device:device.close()

async def ble_run(bridge, args):
    from bleak import BleakClient, BleakScanner
    print("扫描 Passport Music；首次请先在 Windows 蓝牙设置中完成六位码配对。", flush=True)
    devices = await BleakScanner.discover(timeout=8, return_adv=True)
    candidates = [dev for dev, adv in devices.values() if SERVICE in [s.lower() for s in adv.service_uuids]]
    if args.address: candidates=[d for d in candidates if d.address.casefold()==args.address.casefold()]
    if not candidates: raise RuntimeError("未找到设备，请开机并确认蓝牙已启用")
    if len(candidates)!=1: raise RuntimeError("发现多个设备，请使用 --address 选择指定设备")
    # Bleak's Windows custom pairing supports CONFIRM_ONLY, not PROVIDE_PIN.
    # Preserve authenticated passkey pairing: let Windows Settings own first
    # pairing, then connect only to the resulting bonded device.
    if sys.platform == 'win32':
        from winrt.windows.devices.bluetooth import BluetoothLEDevice
        from winrt.windows.devices.enumeration import DeviceInformation
        native=await BluetoothLEDevice.from_bluetooth_address_async(int(candidates[0].address.replace(':','').replace('-',''),16))
        if native is None: raise RuntimeError("无法读取蓝牙设备，请重新扫描")
        try:
            info=await DeviceInformation.create_from_id_async(native.device_information.id)
            if not info.pairing.is_paired:
                raise RuntimeError("请先在 Windows 设置→蓝牙和设备→添加设备中配对 Passport Music，输入设备屏幕六位码")
        finally: native.close()
    async with BleakClient(candidates[0], pair=False, timeout=60) as client, ble_connection_parameters(candidates[0].address):
        await client.start_notify(TX, lambda _sender, data: bridge.received(data))
        logging.getLogger(__name__).info('BLE MTU: %s',client.mtu_size)
        print("蓝牙已连接。按 Ctrl+C 退出。", flush=True)
        metrics_at=0
        # Use small response writes even on default MTU. A newline resynchronizes
        # after interruption. State frames can span any number of BLE writes.
        async def send(data):
            nonlocal metrics_at
            started=time.monotonic()
            if not client.is_connected: raise ConnectionError("蓝牙已断开")
            data=b"\n"+data
            chunk_size=max(20,min(244,client.mtu_size-3))
            for offset in range(0,len(data),chunk_size):
                await client.write_gatt_char(RX, data[offset:offset+chunk_size], response=True)
            elapsed=time.monotonic()-started
            bridge.observe_delivery(elapsed)
            if started>=metrics_at:
                logging.getLogger(__name__).info('State transfer: %d bytes / %d ms; lyric lead %d ms',len(data),round(elapsed*1000),bridge.lyric_lead_ms)
                metrics_at=started+10
        await bridge.run(send)

async def usb_run(bridge, args):
    import serial
    if not args.port: raise ValueError("USB 模式需要 --port COM端口")
    # Opening USB serial does not flash. Avoid deliberate DTR/RTS reset pulses.
    port=serial.Serial()
    port.port=args.port; port.baudrate=115200; port.timeout=0; port.write_timeout=1
    port.dtr=False; port.rts=False; port.open()
    try:
        async def send(data): await asyncio.to_thread(port.write,b"\n"+data)
        async def read(): return port.read(min(1024,port.in_waiting))
        print("USB 已连接。按 Ctrl+C 退出。", flush=True)
        await bridge.run(send,read)
    finally: port.close()

async def main(args):
    if args.debug: logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if args.list_ports:
        from serial.tools.list_ports import comports
        for p in comports(): print(p.device,p.description)
        return
    if args.scan:
        from bleak import BleakScanner
        devices=await BleakScanner.discover(timeout=8,return_adv=True)
        matches=[(d.address,d.name) for d,a in devices.values() if SERVICE in [s.lower() for s in a.service_uuids]]
        print(json.dumps(matches,ensure_ascii=False)); return
    if args.launch_player:
        from ncm_desktop import launch_player
        await launch_player(args.player_exe,args.desktop_port)
    provider=DemoMusic() if args.demo else WindowsMusic(args.desktop_port)
    await provider.initialize()
    if args.diagnose_lyrics:
        state=await provider.snapshot()
        lines,message=await asyncio.to_thread(load_lyrics,state['title'],state['artist'],state['duration'],args.lyrics,not args.offline,state['album'],state.get('song_id')) if state['available'] else ([],"网易云未就绪")
        print(json.dumps(dict(available=state['available'],timed_line_count=len(lines),status=message),ensure_ascii=False))
        return
    if args.diagnose:
        state=await provider.snapshot()
        print(json.dumps(dict(available=state['available'], playing=state['playing'],
            timeline_available=state['duration']>0, internal_volume_available=state['volume']>=0,
            clock_source=state.get('clock_source','smtc'),
            internal_player=provider.native if isinstance(provider,WindowsMusic) else False), ensure_ascii=False))
        return
    bridge=Bridge(provider,args)
    delay=2
    while True:
        try:
            await (usb_run(bridge,args) if args.transport=='usb' else ble_run(bridge,args))
            delay=2
        except Exception as exc:
            print(f"连接或播放器异常：{type(exc).__name__}: {exc}；{delay} 秒后重试",flush=True)
            await asyncio.sleep(delay); delay=min(15,delay*2)

@contextmanager
def bridge_instance(enabled=True):
    """One device bridge per Windows session; diagnostics remain independent."""
    handle=None
    if enabled and sys.platform=='win32':
        import ctypes
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
        api.CreateMutexW.restype=ctypes.c_void_p
        api.CloseHandle.argtypes=[ctypes.c_void_p]
        api.CloseHandle.restype=ctypes.c_bool
        handle=api.CreateMutexW(None,False,r'Local\FoloToy.PassportMusic.DeviceBridge')
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error()==183:
            api.CloseHandle(handle)
            raise RuntimeError('音乐桥接已在运行，请使用现有窗口或先关闭它')
    try:yield
    finally:
        if handle:api.CloseHandle(handle)

def cli():
    parser=argparse.ArgumentParser(description="AI Passport 网易云音乐遥控桥接")
    parser.add_argument('--transport',choices=['ble','usb'],default='ble')
    parser.add_argument('--address',help='多个蓝牙设备时选择地址')
    parser.add_argument('--port',help='USB 串口，例如 COM5')
    parser.add_argument('--lyrics',default=str(Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve().parent/'lyrics'))
    parser.add_argument('--offline',action='store_true',help='只使用本地 LRC，不访问歌词服务')
    parser.add_argument('--demo',action='store_true',help='模拟歌曲，不操作真实播放器')
    parser.add_argument('--diagnose',action='store_true',help='只读检查网易云媒体会话，无需连接设备')
    parser.add_argument('--diagnose-lyrics',action='store_true',help='诊断当前歌曲歌词查询，不输出歌词文本')
    parser.add_argument('--list-ports',action='store_true')
    parser.add_argument('--scan',action='store_true',help='仅扫描音乐固件蓝牙设备，不连接')
    parser.add_argument('--desktop-port',type=int,default=9223,help='网易云本机遥控接口端口')
    parser.add_argument('--launch-player',action='store_true',help='以遥控模式启动已安装的网易云客户端')
    parser.add_argument('--player-exe',help='网易云 cloudmusic.exe 路径')
    parser.add_argument('--debug',action='store_true',help='记录连接和控制诊断，不记录歌曲或歌词文本')
    args=parser.parse_args()
    try:
        with bridge_instance(not any((args.diagnose,args.diagnose_lyrics,args.scan,args.list_ports))):
            asyncio.run(main(args))
    except KeyboardInterrupt: print("已退出")
    except (RuntimeError,ValueError,OSError) as exc:
        print(f'启动失败：{exc}',flush=True)
        raise SystemExit(1)

if __name__=='__main__': cli()
