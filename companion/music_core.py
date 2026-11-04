"""Platform-independent framing, lyrics and matching. No account credentials."""
import bisect
import json
import re
import unicodedata
import logging
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit, unquote
from urllib.request import Request, build_opener, ProxyHandler, getproxies, proxy_bypass

PREFIX = b"FAPM1 "
SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
ACTIONS = {"volume_up", "volume_down", "volume_up_20", "volume_down_20", "previous", "next", "toggle", "lyric_previous", "lyric_next", "toggle_desktop_lyrics"}

def utf8_limit(text, limit):
    return str(text).replace("\x00", "").encode("utf-8")[:limit].decode("utf-8", "ignore")

def frame(state):
    state = dict(state, type="state")
    for key in ("title", "artist", "album", "message"):
        state[key] = utf8_limit(state.get(key, ""), 192)
    for key in ("lyric", "before", "after"):
        state[key] = utf8_limit(state.get(key, ""), 384)
    result = PREFIX + json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
    if len(result) >= 4096:
        raise ValueError("snapshot exceeds firmware frame budget")
    return result

class CommandDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.dropping = False
        self.last_id = -1
        self.boot = None
        self.offset_ms=None

    def feed(self, data):
        commands = []
        for byte in data:
            if byte == 10:
                if not self.dropping and self.buffer.startswith(PREFIX):
                    try:
                        obj = json.loads(self.buffer[len(PREFIX):])
                        ident = obj.get("id")
                        boot = obj.get("boot", 0)
                        offset=obj.get('lyric_offset_ms')
                        if (obj.get('type')=='settings' and type(boot) is int and 0<=boot<=0xffffffff
                                and type(offset) is int and -2000<=offset<=2000 and offset%50==0):
                            self.offset_ms=offset
                        if (obj.get("type") == "command" and type(ident) is int and 0 <= ident <= 0xffffffff
                                and type(boot) is int and 0 <= boot <= 0xffffffff
                                and obj.get("action") in ACTIONS):
                            if boot != self.boot:
                                self.boot = boot; self.last_id = -1
                            if ident > self.last_id:
                                self.last_id = ident
                                commands.append(obj["action"])
                    except (ValueError, TypeError, AttributeError):
                        pass
                self.buffer.clear(); self.dropping = False
            elif not self.dropping:
                if len(self.buffer) >= 512 or byte == 0:
                    self.buffer.clear(); self.dropping = True
                else:
                    self.buffer.append(byte)
        return commands

def parse_lrc(text):
    """Multiple timestamps, offset (milliseconds), CRLF and fractional seconds."""
    match = re.search(r"\[offset:([+-]?\d+)\]", text, re.I)
    offset = int(match[1]) if match else 0
    result = []
    for line in text.splitlines():
        stamps = list(re.finditer(r"\[(\d{1,3}):([0-5]\d)(?:[.:](\d{1,3}))?\]", line))
        if not stamps:
            continue
        words = line[stamps[-1].end():].strip()
        for stamp in stamps:
            minutes, seconds, fraction = stamp.groups()
            ms = int(minutes)*60000 + int(seconds)*1000 + int((fraction or "0").ljust(3, "0")) + offset
            result.append((max(0, ms), words))
    return sorted(result, key=lambda entry: entry[0])

def lyric_window(lines, position):
    index = bisect.bisect_right([t for t, _ in lines], position) - 1
    def at(i): return lines[i][1] if 0 <= i < len(lines) else ""
    return at(index-1) if index >= 0 else "", at(index), at(index+1)

def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())

def safe_name(title, artist):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", f"{title} - {artist}")[:120].rstrip(". ") or "track"

def http_json(url, data=None):
    # NetEase's domestic endpoints normally work directly. A stale local proxy
    # must not break lyrics after FlClash exits or changes its connection state.
    try:
        return _http_json_once(url, data)
    except (OSError, ValueError):
        target = urlsplit(url)
        proxy = getproxies().get(target.scheme)
        if not proxy or proxy_bypass(target.hostname):
            raise
        logging.getLogger(__name__).info('Direct lyric request failed; trying configured proxy')
        # Re-read proxy settings on each failed request; never cache a route.
        return _http_json_once(url, data, proxy)


def _http_json_once(url, data=None, proxy=None):
    if sys.platform == 'win32':
        # Native WinHTTP uses Windows certificate validation and works in the
        # packaged EXE without Python OpenSSL configuration/provider files.
        import comtypes
        from comtypes.client import CreateObject
        initialized=False
        try:
            comtypes.CoInitialize(); initialized=True
        except OSError as exc:
            if getattr(exc,'winerror',None) not in (-2147417850,0x80010106): raise
        try:
            request=CreateObject('WinHttp.WinHttpRequest.5.1',dynamic=True)
            request.SetTimeouts(6000,6000,6000,6000)
            request.Open('POST' if data is not None else 'GET',url,False)
            if proxy:
                endpoint=urlsplit(proxy if '://' in proxy else 'http://'+proxy)
                if endpoint.scheme!='http' or not endpoint.hostname:
                    raise OSError('Unsupported lyric proxy; HTTP CONNECT proxy required')
                host='['+endpoint.hostname+']' if ':' in endpoint.hostname else endpoint.hostname
                request.SetProxy(2,host+':'+str(endpoint.port or 80))
                if endpoint.username is not None:
                    request.SetCredentials(unquote(endpoint.username),unquote(endpoint.password or ''),1)
            else:
                # Explicit DIRECT also overrides the machine WinHTTP defaults.
                request.SetProxy(1)
            request.SetRequestHeader('User-Agent','Mozilla/5.0')
            request.SetRequestHeader('Referer','https://music.163.com/')
            if data is not None:
                request.SetRequestHeader('Content-Type','application/x-www-form-urlencoded; charset=UTF-8')
                request.Send(data.decode('ascii'))
            else: request.Send()
            if request.Status!=200: raise OSError(f'HTTP {request.Status}')
            raw=request.ResponseText
            if len(raw)>2_000_000: raise ValueError('oversized lyric response')
            return json.loads(raw)
        except comtypes.COMError as exc:
            # COM transport errors aren't OSError; normalize so the bridge's
            # transient failure/retry policy also covers native request timeouts.
            raise OSError('Windows lyric request failed') from exc
        finally:
            if initialized: comtypes.CoUninitialize()
    req = Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"})
    # An explicit handler avoids urllib's process-wide cached default opener.
    routes = {urlsplit(url).scheme: proxy} if proxy else {}
    with build_opener(ProxyHandler(routes)).open(req, timeout=6) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000: raise ValueError("oversized lyric response")
    return json.loads(raw)

def matching_songs(songs, title, artist, duration, album=""):
    """Exact title/artist; album and duration narrow the recording when available."""
    candidates = []
    for song in songs:
        artists = song.get("artists", song.get("ar", []))
        names = [a.get("name", "") for a in artists]
        if normalize(song.get("name", "")) != normalize(title): continue
        joined = {normalize("".join(names)), *(normalize(n) for n in names)}
        if not normalize(artist) or normalize(artist) not in joined: continue
        length = song.get("duration", song.get("dt", 0))
        if duration and length and abs(duration-length) > 3000: continue
        candidates.append(song)
    if album:
        exact = [song for song in candidates if normalize(song.get('album',{}).get('name','')) == normalize(album)]
        if exact: candidates=exact
    if duration and len(candidates)>1:
        closest=min(abs(duration-song.get('duration',song.get('dt',0))) for song in candidates)
        candidates=[song for song in candidates if abs(duration-song.get('duration',song.get('dt',0)))==closest]
    return candidates

def find_song(songs, title, artist, duration, album=""):
    candidates=matching_songs(songs,title,artist,duration,album)
    ids = {song['id'] for song in candidates}
    return next(iter(ids)) if len(ids) == 1 else None

def load_lyrics(title, artist, duration, directory, online=True, album="", song_id=None):
    path = Path(directory) / (safe_name(title, artist) + ".lrc")
    if path.is_file():
        lines = parse_lrc(path.read_text(encoding="utf-8-sig"))
        return lines, "本地歌词" if lines else "本地文件没有时间标签"
    if not online: return [], "离线：请放入同名 LRC 文件"
    try:
        if type(song_id) is int and 0<song_id<2**63:
            ident=song_id;songs=[]
        else:
            data = urlencode({"s": f"{title} {artist}", "type": 1, "limit": 10}).encode()
            results = http_json("https://music.163.com/api/search/get", data)
            songs=results.get("result", {}).get("songs", [])
            ident = find_song(songs, title, artist, duration, album)
        manual=False
        if ident is None:
            candidates=matching_songs(songs,title,artist,duration,album)
            lengths=[s.get('duration',s.get('dt',0)) for s in candidates]
            # Missing client timeline: repeated album entries can still supply
            # manually browsed lyrics. Never claim timing/version certainty.
            if duration or len(candidates)<2 or not all(lengths) or max(lengths)-min(lengths)>3000:
                return [], "歌词未匹配，请使用本地 LRC"
            ids=list(dict.fromkeys(s['id'] for s in candidates))[:3]
            manual=True
        else: ids=[ident]
        last_error=None
        for ident in ids:
            try:
                response = http_json("https://music.163.com/api/song/lyric?" + urlencode({"id": ident, "lv": -1, "kv": -1, "tv": -1}))
                lines = parse_lrc(response.get("lrc", {}).get("lyric", ""))
                if lines: return lines,"同名歌词（手动）" if manual else "在线歌词"
            except (OSError,ValueError,KeyError,TypeError) as exc:
                logging.getLogger(__name__).warning('Lyric endpoint failed (%s): %s',type(exc).__name__,exc)
                last_error=exc
        if last_error: return [],"歌词查询失败，稍后自动重试"
        return [],"纯音乐或暂无歌词"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logging.getLogger(__name__).warning('Lyric search failed (%s): %s',type(exc).__name__,exc)
        return [], "歌词查询失败，稍后自动重试"
