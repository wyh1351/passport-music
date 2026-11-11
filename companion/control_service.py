"""Windows operations for the control center. Slow work stays off the UI thread."""
import asyncio
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from background_music import (BRIDGE, LAUNCHER, PAUSE_FILE, registered, run_command,
                              owned_process, request_stop, spawn, set_autostart)
from background_task import configure_recovery_task
from control_model import read_json, status_view, port_available, save_port, port_number
from passport_music import configured_desktop_port


def collect_status(root):
    import psutil
    root = Path(root)
    record = read_json(root/'background-state.json')
    pid = record.get('bridge')
    bridge = owned_process(pid, root/BRIDGE) if type(pid) is int else None
    supervisor_pid = record.get('supervisor')
    supervisor = owned_process(supervisor_pid, root/LAUNCHER, True) if type(supervisor_pid) is int else None
    running = bool(bridge and supervisor)
    player = {}
    config_error = ''
    try:
        port = configured_desktop_port(root/'desktop-port.txt')
        result = subprocess.run([str(root/BRIDGE), '--diagnose'], cwd=root,
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=8)
        result.check_returncode()
        raw = result.stdout
        try: text = raw.decode('utf-8')
        except UnicodeDecodeError: text = raw.decode('gb18030', errors='replace')
        player = json.loads(text.strip().splitlines()[-1])
    except ValueError:
        port = 9223
        config_error = '端口配置无效，请在设置中重新保存。'
        player['probe_error'] = True
    except (OSError, subprocess.SubprocessError, IndexError):
        port = 9223
        try: port = configured_desktop_port(root/'desktop-port.txt')
        except (ValueError, OSError): pass
        player['probe_error'] = True
    player['process_running'] = any((p.info['name'] or '').lower() == 'cloudmusic.exe'
                                   for p in psutil.process_iter(['name']))
    if not player.get('internal_player'):
        player['port_blocked'] = not port_available(port)
    paused = (root/PAUSE_FILE).exists()
    health = read_json(root/'bridge-status.json')
    view = status_view(health, player, running, paused, pid=pid)
    if config_error:
        view.update(heading='端口配置需要修正', detail=config_error, action='settings')
    return dict(view, running=running, paused=paused, autostart=registered()==run_command(root),
                port=port, player=player, health=health)


def restart_bridge(root):
    request_stop(Path(root))
    spawn(Path(root))


def change_port(root, value):
    number = port_number(value)
    previous = configured_desktop_port(Path(root)/'desktop-port.txt')
    if number != previous and not port_available(number):
        raise ValueError('这个端口已被占用或被 Windows 保留，请选择其他端口。')
    save_port(root, number)
    restart_bridge(root)
    return number


def enable_startup(root, enabled):
    # Changing login behavior does not stop current music control.
    set_autostart(Path(root), enabled)
    configure_recovery_task(Path(root)/LAUNCHER, enabled)


def open_player(root, restart=False):
    from ncm_desktop import launch_player, locate_player
    root = Path(root)
    executable = locate_player()
    if restart:
        import psutil
        stopped = []
        for process in psutil.process_iter(['name', 'exe', 'username']):
            if ((process.info['name'] or '').lower()=='cloudmusic.exe'
                    and process.info['exe'] and Path(process.info['exe']).resolve()==executable.resolve()
                    and process.info['username']==psutil.Process().username()):
                try: process.terminate(); stopped.append(process)
                except psutil.NoSuchProcess: pass
        psutil.wait_procs(stopped, timeout=4)
    asyncio.run(launch_player(str(executable), configured_desktop_port(root/'desktop-port.txt')))
    show_player(executable)


def player_window_candidates(executable):
    """Inspect only this user's player windows, including a hidden tray window."""
    import psutil
    user=psutil.Process().username()
    pids=set()
    for process in psutil.process_iter(['exe','username']):
        if process.info['exe'] and process.info['username']==user and Path(process.info['exe']).resolve()==Path(executable).resolve():
            pids.add(process.pid)
    api=ctypes.WinDLL('user32',use_last_error=True)
    api.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    api.IsWindowVisible.argtypes=[ctypes.c_void_p]
    api.GetWindow.argtypes=[ctypes.c_void_p,ctypes.c_uint];api.GetWindow.restype=ctypes.c_void_p
    api.GetWindowTextLengthW.argtypes=[ctypes.c_void_p]
    api.GetWindowRect.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.RECT)]
    api.ShowWindow.argtypes=[ctypes.c_void_p,ctypes.c_int]
    api.SetForegroundWindow.argtypes=[ctypes.c_void_p]
    callback_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    windows=[]
    def consider(hwnd,_):
        pid=ctypes.c_ulong();api.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids:
            rect=wintypes.RECT()
            if api.GetWindowRect(hwnd,ctypes.byref(rect)):
                windows.append(dict(handle=hwnd,visible=bool(api.IsWindowVisible(hwnd)),
                    owned=bool(api.GetWindow(hwnd,4)),titled=api.GetWindowTextLengthW(hwnd)>0,
                    width=rect.right-rect.left,height=rect.bottom-rect.top))
        return True
    api.EnumWindows.argtypes=[callback_type,ctypes.c_void_p]
    api.EnumWindows(callback_type(consider),None)
    return api,windows


def select_player_window(windows):
    # Visibility alone is insufficient: closing to the tray hides the main
    # window. Reject small helpers/owned dialogs; prefer the largest main view.
    candidates=[w for w in windows if not w['owned'] and w['titled']
                and w['width']>=320 and w['height']>=200]
    return max(candidates,key=lambda w:w['width']*w['height']) if candidates else None


def show_player(executable):
    """Restore the original main window, whether minimized or hidden to tray."""
    for attempt in range(12):
        api,windows=player_window_candidates(executable)
        window=select_player_window(windows)
        if window:
            api.ShowWindow(window['handle'],9)  # SW_RESTORE also shows hidden windows.
            api.SetForegroundWindow(window['handle'])
            if api.IsWindowVisible(window['handle']):return True
        if attempt==0:
            # NetEase's single-instance entry can recreate a disposed tray
            # window without terminating the process or interrupting playback.
            startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=1
            subprocess.Popen([str(executable)],cwd=Path(executable).parent,startupinfo=startup)
        time.sleep(.25)
    raise RuntimeError('未能显示网易云窗口。请从电脑托盘打开网易云后重试；当前播放和连接已保留。')


def install_package(root):
    result = subprocess.run([str(Path(root)/LAUNCHER), '--install', '--quiet'], cwd=root,
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=50)
    result.check_returncode()
