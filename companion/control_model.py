"""Desktop status, preferences and recovery actions; independent from the UI."""
import json
import os
from pathlib import Path
import socket
import time

VERSION = 'v1.3.0'
STATUS_FILE = 'bridge-status.json'


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


class BridgeStatus:
    """Publish only health fields, never song titles, lyrics or device addresses."""
    def __init__(self, root):
        self.path = Path(root) / STATUS_FILE
        self.data = {}
        self.written = 0

    def update(self, phase=None, **fields):
        if phase is not None:
            fields['phase'] = phase
        data = dict(self.data, **fields)
        now = time.time()
        if data == self.data and now - self.written < 2:
            return
        self.data = data
        self.written = now
        try:
            atomic_json(self.path, dict(data, pid=os.getpid(), updated=now))
        except OSError:
            pass  # A read-only package must not break music control.


def port_number(value):
    text = str(value).strip()
    if not text.isascii() or not text.isdecimal() or len(text) > 5 or not 1024 <= int(text) <= 65535:
        raise ValueError('端口必须是 1024～65535 之间的整数。')
    return int(text)


def installation_present(root, startup_command, expected_command):
    root=Path(root)
    marker=read_json(root/'installation.json')
    return startup_command==expected_command or (marker.get('schema')==1 and marker.get('installed') is True
            and (root/'PassportMusicBackground.exe').is_file() and (root/'PassportMusic.exe').is_file())


def save_port(root, value):
    number = port_number(value)
    path = Path(root) / 'desktop-port.txt'
    temp = path.with_suffix('.tmp')
    temp.write_text(str(number) + '\n', encoding='utf-8')
    os.replace(temp, path)
    return number


def port_available(port):
    try:
        with socket.socket() as connection:
            connection.bind(('127.0.0.1', port_number(port)))
        return True
    except OSError:
        return False


def status_view(health, player, running, paused=False, now=None, pid=None):
    """Do not show a disconnected/stale process as a healthy connection."""
    now = time.time() if now is None else now
    updated = health.get('updated', 0)
    fresh = (type(updated) in (int, float) and 0 <= now-updated <= 10
             and (pid is None or health.get('pid') == pid))
    phase = health.get('phase') if fresh else None
    connected = running and not paused and phase == 'connected'
    device = '已暂停连接' if paused else '后台未运行' if not running else '已连接' if connected else '正在连接'
    native = player.get('internal_player') is True
    if native:
        music = '播放中' if player.get('playing') else '已就绪' if player.get('available') else '等待播放歌曲'
    elif player.get('process_running'):
        music = '控制端口不可用' if player.get('port_blocked') else '遥控接口未开启'
    else:
        music = '尚未打开' if not player.get('probe_error') else '检查未完成'
    lyric = {'ready': '已同步', 'loading': '正在查找', 'error': '查询失败，将重试',
             'missing': '未找到在线歌词'}.get(health.get('lyrics'), '等待歌曲') if connected else '等待连接'
    if paused or not running:
        heading, detail, action = '连接已暂停' if paused else '后台未运行', '开始连接后，设备会自动寻找电脑。', 'start'
    elif not native:
        heading = music
        detail = ('当前端口无法使用。请在设置中更换端口，并同步网易云的启动参数。' if player.get('port_blocked') else
                  '请打开网易云并播放歌曲。已打开时，完全退出后使用本软件重新打开。')
        action = 'settings' if player.get('port_blocked') else 'player'
    elif not connected:
        heading, detail, action = '等待 Passport 连接', '保持设备开机和电脑蓝牙开启；首次使用需在 Windows 中完成六位码配对。', 'bluetooth'
    elif health.get('lyrics') == 'error':
        heading, detail, action = '音乐控制正常，歌词暂不可用', '在线查询会自动重试。请检查电脑网络，或切换一首歌曲后再试。', 'help'
    else:
        heading, detail, action = '可以使用遥控器了', '设备已连接，网易云已就绪。', 'none'
    return dict(device=device, music=music, lyrics=lyric, heading=heading, detail=detail, action=action,
                connected=connected, ready=connected and native)
