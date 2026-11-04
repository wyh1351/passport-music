"""Loopback-only adapter for NetEase desktop's own player state and controls.

No client files are patched. The caller launches the stock client with its CEF
debug port, validates the application/page, and uses a fixed command allowlist.
"""
import asyncio
import json
import math
from pathlib import Path
import subprocess
import sys
from http.client import HTTPConnection
from urllib.parse import urlsplit

VOLUME_STEPS = {'volume_up':.05,'volume_down':-.05,'volume_up_20':.20,'volume_down_20':-.20}

FIND_STORE = r"""(()=>{
 const root=document.getElementById('root');
 const pending=[root?._reactRootContainer?._internalRoot?.current], visited=new Set();
 while(pending.length && visited.size<1000){
  const node=pending.pop(); if(!node||visited.has(node))continue;visited.add(node);
  const candidate=node.memoizedProps?.store;
  if(candidate&&typeof candidate.getState==='function'&&candidate.getState().playing){
   window.__passportMusicStore=candidate;return true;
  }
  pending.push(node.child,node.sibling);
 }
 throw new Error('NetEase player state not found');
})()"""

INSTALL_CLOCK = r"""(()=>{
 if(window.__passportAudioClock?.version===1)return true;
 if(!window.webpackJsonp?.push)return false;
 if(!window.__passportMusicRequire)window.webpackJsonp.push([
  ['passport_music_capture_v1'],{'passport_music_capture_v1':function(m,e,r){window.__passportMusicRequire=r;}},[['passport_music_capture_v1']]]);
 const modules=window.__passportMusicRequire?.c;
 if(!modules)return false;
 let player;
 for(const m of Object.values(modules).slice(0,10000)){
  const candidate=m.exports?.AudioPlayer;
  if(candidate&&typeof candidate.subscribePlayStatus==='function'){player=candidate;break;}
 }
 if(!player)return false;
 const clock={version:1,position:null,track:'',at:0};
 const record=(info,field)=>{
  const value=info[field];
  if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>86400)return;
  const p=window.__passportMusicStore.getState().playing,t=p.curTrack||p.curPlaying?.track||{};
  clock.position=value*1000;clock.track=String(t.id||p.onlineResourceId||p.resourceTrackId||'');clock.at=performance.now();
 };
 player.subscribePlayStatus({type:'playprogress',callback:info=>record(info,'current')});
 player.subscribePlayStatus({type:'seek',callback:info=>{if(info.code===0)record(info,'position');}});
 window.__passportAudioClock=clock;
 return true;
})()"""

SNAPSHOT = r"""(()=>{
 const p=window.__passportMusicStore.getState().playing;
 const t=p.curTrack||p.curPlaying?.track||{};
 const seconds=Number(p.resourceDuration)||(Number(t.duration)||0)/1000;
 const sliders=Array.from(document.querySelectorAll('input[type=range]'));
 const seek=sliders.find(e=>Number(e.max)>1&&Math.abs(Number(e.max)-seconds)<2);
 const track=String(t.id||p.onlineResourceId||p.resourceTrackId||'');
 const clock=window.__passportAudioClock;
 const pos=seek?Number(seek.value)*1000:null;
 const artists=p.resourceArtists||t.artists||[];
 return {title:t.name||p.resourceName||'',artist:artists.map(a=>a.name||'').join(' / '),
  album:t.album?.albumName||t.album?.name||'',song_id:track,
  duration:seek?Number(seek.max)*1000:seconds*1000,position:pos,
  audio_position:clock?.position??null,audio_track:clock?.track??'',audio_age:clock?performance.now()-clock.at:null,
  volume:Number(p.playingVolume)*100,playing:p.playingState===2,
  desktop_lyrics:window.__passportMusicStore.getState().setting?.showLyric};
})()"""

# Reuse the same native hotkey effect as NetEase's own desktop-lyrics shortcut.
# It opens/closes the native overlay and persists showLyric together. Do not just
# flip Redux state: that changes the icon without controlling the actual window.
TOGGLE_DESKTOP_LYRICS = r"""(async()=>{
 const s=window.__passportMusicStore,before=s.getState().setting?.showLyric;
 if(typeof before!=='boolean')throw new Error('Desktop lyrics unavailable');
 s.dispatch({type:'setting/handleHotkey',payload:{name:'lyric',global:true}});
 for(let i=0;i<20;i++){
  await new Promise(r=>setTimeout(r,25));
  const after=s.getState().setting?.showLyric;
  if(after===!before)return {before,after};
 }
 throw new Error('Desktop lyrics did not change');
})()"""

def validate_target(version, targets, port):
    if 'NeteaseMusicDesktop/' not in str(version.get('User-Agent','')):
        raise RuntimeError('Local port does not belong to NetEase Music')
    matches=[t for t in targets if t.get('type')=='page' and t.get('url')=='orpheus://orpheus/pub/app.html']
    if len(matches)!=1: raise RuntimeError('NetEase main page is missing or ambiguous')
    url=matches[0].get('webSocketDebuggerUrl','')
    parsed=urlsplit(url)
    if parsed.scheme!='ws' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.port!=port or parsed.username:
        raise RuntimeError('Refusing non-loopback player interface')
    return url

def normalize_snapshot(raw):
    if not isinstance(raw,dict): raise ValueError('Invalid player snapshot')
    def number(key,low,high,nullable=False):
        v=raw.get(key)
        if nullable and v is None:return None
        if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high:
            raise ValueError('Invalid player '+key)
        return int(round(v))
    duration=number('duration',0,86400000)
    position=number('position',0,86400000,True)
    song_id=str(raw.get('song_id',''))
    audio=raw.get('audio_position');age=raw.get('audio_age')
    valid_audio=(type(audio) in (int,float) and math.isfinite(audio) and 0<=audio<=86400000
        and type(age) in (int,float) and math.isfinite(age) and age>=0
        and bool(song_id) and raw.get('audio_track')==song_id
        and (raw.get('playing') is not True or age<2000))
    if valid_audio:position=int(round(audio))
    # No invented clock if neither a current native event nor seek value exists.
    if position is None: duration=0;position=0
    elif duration: position=min(position,duration)
    volume=number('volume',0,100)
    return dict(title=str(raw.get('title','')),artist=str(raw.get('artist','')),album=str(raw.get('album','')),
        song_id=int(song_id) if song_id.isdigit() and 0<int(song_id)<2**63 else None,
        position=position,duration=duration,volume=volume,playing=raw.get('playing') is True,
        available=bool(raw.get('title')),clock_source='audio' if valid_audio else 'seek',
        desktop_lyrics=int(raw['desktop_lyrics']) if type(raw.get('desktop_lyrics')) is bool else -1)

class DesktopPlayer:
    def __init__(self,port=9223):
        self.port=port;self.socket=None;self.ident=0;self.lock=asyncio.Lock()

    def discover(self):
        # Never send local discovery through a proxy.
        def get(path):
            connection=HTTPConnection('127.0.0.1',self.port,timeout=2)
            try:
                connection.request('GET','/'+path)
                response=connection.getresponse()
                if response.status!=200:raise OSError('Local player HTTP error')
                data=response.read(1_000_001)
            finally:connection.close()
            if len(data)>1_000_000:raise ValueError('Oversized discovery response')
            return json.loads(data)
        return validate_target(get('json/version'),get('json/list'),self.port)

    async def connect(self):
        from websockets.asyncio.client import connect
        url=await asyncio.to_thread(self.discover)
        # This client's CEF closes the CDP socket on a WebSocket control ping.
        # Repeated bounded CDP requests provide liveness without those pings.
        self.socket=await connect(url,proxy=None,ping_interval=None,open_timeout=3,close_timeout=1,max_size=2_000_000)
        try:
            await self.evaluate(FIND_STORE)
            await self.evaluate(INSTALL_CLOCK)
        except BaseException:await self.close();raise

    async def close(self):
        socket,self.socket=self.socket,None
        if socket:await socket.close()

    async def evaluate(self,expression):
        async with self.lock:
            if not self.socket:raise ConnectionError('Player interface disconnected')
            self.ident+=1; ident=self.ident
            await self.socket.send(json.dumps(dict(id=ident,method='Runtime.evaluate',params=dict(
                expression=expression,returnByValue=True,awaitPromise=True))))
            async with asyncio.timeout(3):
                while True:
                    response=json.loads(await self.socket.recv())
                    if response.get('id')!=ident:continue
                    result=response.get('result',{})
                    if response.get('error') or result.get('exceptionDetails'):
                        raise RuntimeError('NetEase player interface rejected operation')
                    return result.get('result',{}).get('value')

    async def snapshot(self):
        if not self.socket:await self.connect()
        try:return normalize_snapshot(await self.evaluate(SNAPSHOT))
        except BaseException:await self.close();raise

    async def command(self,action):
        if action=='toggle_desktop_lyrics':
            result=await self.evaluate(TOGGLE_DESKTOP_LYRICS)
            if (not isinstance(result,dict) or type(result.get('before')) is not bool
                    or type(result.get('after')) is not bool or result['before']==result['after']):
                raise RuntimeError('Desktop lyrics did not change')
            return result
        if action in VOLUME_STEPS:
            step=VOLUME_STEPS[action]
            expression="""(async()=>{const s=window.__passportMusicStore;
             const before=Number(s.getState().playing.playingVolume);
             const target=Math.max(0,Math.min(1,before+STEP));
             s.dispatch({type:'playing/setVolume',payload:{volume:target}});
             await new Promise(r=>setTimeout(r,120));
             return {before:Math.round(before*100),after:Math.round(s.getState().playing.playingVolume*100)};
            })()""".replace('STEP',str(step))
            return await self.evaluate(expression)
        commands={
            'next':dict(type='playingList/jump2Track',payload=dict(flag=1,type='call',triggerScene='hotKey')),
            'previous':dict(type='playingList/jump2Track',payload=dict(flag=-1,type='call',triggerScene='hotKey')),
        }
        if action=='toggle':
            return await self.evaluate("""(()=>{const s=window.__passportMusicStore;
             const action=s.getState().playing.playingState===2?'playing/pause':'playing/resume';
             s.dispatch({type:action,payload:{triggerScene:'hotKey'}});return true;})()""")
        if action not in commands:raise ValueError('Unsupported player command')
        return await self.evaluate('(()=>{window.__passportMusicStore.dispatch('+json.dumps(commands[action])+');return true;})()')

def locate_player(explicit=None):
    import psutil
    candidates=[explicit] if explicit else []
    for process in psutil.process_iter(['name','exe']):
        if (process.info.get('name') or '').casefold()=='cloudmusic.exe':
            candidates.append(process.info.get('exe'))
    if sys.platform=='win32':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive,r'Software\Microsoft\Windows\CurrentVersion\App Paths\cloudmusic.exe',0,winreg.KEY_READ|view) as key:
                        candidates.append(winreg.QueryValueEx(key,None)[0])
                except OSError: pass
                try:
                    with winreg.OpenKey(hive,r'Software\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view) as parent:
                        for index in range(winreg.QueryInfoKey(parent)[0]):
                            try:
                                with winreg.OpenKey(parent,winreg.EnumKey(parent,index)) as key:
                                    name=winreg.QueryValueEx(key,'DisplayName')[0]
                                    if '网易云音乐' not in name: continue
                                    try:candidates.append(str(Path(winreg.QueryValueEx(key,'InstallLocation')[0])/'cloudmusic.exe'))
                                    except OSError:pass
                                    try:
                                        icon=winreg.QueryValueEx(key,'DisplayIcon')[0].split(',')[0].strip('"')
                                        candidates.append(str(Path(icon).with_name('cloudmusic.exe')))
                                    except OSError:pass
                            except OSError:pass
                except OSError:pass
    for value in candidates:
        if value:
            path=Path(value)
            if path.name.casefold()=='cloudmusic.exe' and path.is_file():return path
    raise RuntimeError('无法找到网易云，请使用 --player-exe 指定 cloudmusic.exe')

async def launch_player(explicit=None,port=9223):
    if not 1024<=port<=65535:raise ValueError('Invalid local player port')
    player=await asyncio.to_thread(locate_player,explicit)
    probe=DesktopPlayer(port)
    try:
        await asyncio.to_thread(probe.discover)
        return
    except (OSError,ValueError,RuntimeError):pass
    import psutil
    if any((p.info.get('name') or '').casefold()=='cloudmusic.exe' for p in psutil.process_iter(['name'])):
        raise RuntimeError('请先完全退出网易云（含托盘实例），再运行遥控启动器')
    # Refuse to replace another program's local listener.
    import socket
    with socket.socket() as check:
        if check.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('遥控接口端口已被其他程序占用')
    startup=None
    if sys.platform=='win32':
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    subprocess.Popen([str(player),f'--remote-debugging-port={port}','--remote-debugging-address=127.0.0.1'],cwd=player.parent,startupinfo=startup)
    for _ in range(15):
        try:
            await asyncio.to_thread(probe.discover);return
        except (OSError,ValueError,RuntimeError):await asyncio.sleep(1)
    raise RuntimeError('网易云遥控接口未就绪，请检查客户端版本')
