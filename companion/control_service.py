"""Windows operations for the control center. Slow work stays off the UI thread."""
import asyncio
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from background_music import (BRIDGE, LAUNCHER, PAUSE_FILE, registered, run_command,
                              owned_process, request_stop, spawn, set_autostart)
from background_task import configure_recovery_task
from control_model import read_json, status_view, port_available, save_port, port_number, installation_present
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
    root=Path(root)
    with tempfile.TemporaryDirectory(prefix='passport-install-') as directory:
        receipt=Path(directory)/'result.json'
        try:
            result=subprocess.run([str(root/LAUNCHER),'--install','--quiet','--result-file',str(receipt)],
                cwd=root,creationflags=subprocess.CREATE_NO_WINDOW,timeout=65,capture_output=True)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('后台安装超时，请查看诊断日志，确认没有其他安装正在运行后再试。') from exc
        data=read_json(receipt)
        if result.returncode or data.get('ok') is not True:
            raise RuntimeError(data.get('error') or '后台安装未完成，请查看诊断日志后重试。')
        destination=Path(data['directory'])
        if not installation_present(destination,None,'installed'):
            raise RuntimeError('后台文件检查未通过，请重新解压完整电脑包后再安装。')
        state=read_json(destination/'background-state.json')
        if not (owned_process(state.get('supervisor'),destination/LAUNCHER,True)
                and owned_process(state.get('bridge'),destination/BRIDGE)):
            raise RuntimeError('后台已安装，但未保持运行。请查看诊断日志后重新连接设备。')
        return destination


def monitor_work_areas():
    """Return current monitor work areas, cursor monitor first, without taskbars."""
    api=ctypes.WinDLL('user32',use_last_error=True)
    areas=[]
    callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p,
                              ctypes.POINTER(wintypes.RECT),ctypes.c_void_p)
    class MonitorInfo(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
    api.GetMonitorInfoW.argtypes=[ctypes.c_void_p,ctypes.POINTER(MonitorInfo)]
    api.EnumDisplayMonitors.argtypes=[ctypes.c_void_p,ctypes.c_void_p,callback,ctypes.c_void_p]
    def collect(handle,*_):
        info=MonitorInfo();info.size=ctypes.sizeof(info)
        if api.GetMonitorInfoW(handle,ctypes.byref(info)):
            rect=info.work;areas.append((rect.left,rect.top,rect.right,rect.bottom))
        return True
    api.EnumDisplayMonitors(None,None,callback(collect),None)
    point=wintypes.POINT()
    if api.GetCursorPos(ctypes.byref(point)):
        areas.sort(key=lambda r:not (r[0]<=point.x<r[2] and r[1]<=point.y<r[3]))
    return areas


def position_window(app,x,y):
    # Native absolute placement handles monitors left of the primary display;
    # Tk's negative geometry offsets otherwise mean distance from the right edge.
    api=ctypes.WinDLL('user32',use_last_error=True)
    api.SetWindowPos.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,
                              ctypes.c_int,ctypes.c_int,ctypes.c_uint]
    if not api.SetWindowPos(int(app.frame(),0),None,x,y,0,0,0x15):
        raise ctypes.WinError(ctypes.get_last_error())


def window_position(app):
    api=ctypes.WinDLL('user32',use_last_error=True)
    api.GetWindowRect.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.RECT)]
    rect=wintypes.RECT()
    if not api.GetWindowRect(int(app.frame(),0),ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    return dict(x=rect.left,y=rect.top,width=app.winfo_width(),height=app.winfo_height())
