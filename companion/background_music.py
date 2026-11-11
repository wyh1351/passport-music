"""Per-user, windowless logon supervisor. Does not launch or patch NetEase."""
import argparse
import base64
import ctypes
import json
import logging
import locale
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

from background_task import configure_recovery_task

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME = 'FoloToyPassportMusic'
LAUNCHER = 'PassportMusicBackground.exe'
BRIDGE = 'PassportMusic.exe'
CONTROL = 'PassportMusicControl.exe'
PAUSE_FILE = 'background-paused'
INSTALL_KEY = r'Software\FoloToy\PassportMusic'

def decode_bridge_line(line, fallback=None):
    try: return line.decode('utf-8')
    except UnicodeDecodeError: return line.decode(fallback or locale.getencoding(), errors='replace')

def run_command(root):
    path = str(Path(root) / LAUNCHER)
    if '"' in path: raise ValueError('Invalid executable path')
    command = '"' + path + '" --background'
    if len(command) > 260: raise ValueError('Windows logon command exceeds 260 characters')
    return command

def persisted_root():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, INSTALL_KEY) as key:
            saved = Path(winreg.QueryValueEx(key, 'InstallPath')[0])
            if saved.is_absolute() and (saved / LAUNCHER).is_file():
                return saved
    except (ImportError, OSError, TypeError, ValueError):
        pass
    return None


def install_root():
    saved = persisted_root()
    if saved is not None:
        return saved
    command = registered()
    if isinstance(command, str) and command.startswith('"') and command.endswith('" --background'):
        candidate = Path(command[1:-len('" --background')])
        if candidate.is_absolute() and candidate.name == LAUNCHER:
            return candidate.parent
    return Path(os.environ['LOCALAPPDATA']) / 'FoloToy' / 'PassportMusic'

def own_root():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent

def registered():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, RUN_NAME)[0]
    except FileNotFoundError: return None

def set_autostart(root, enabled):
    import winreg
    expected = run_command(root)
    previous = registered()
    if previous not in (None, expected):
        raise RuntimeError('A different Passport autostart entry exists; it was preserved')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled: winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, expected)
        elif previous is not None: winreg.DeleteValue(key, RUN_NAME)

def owned_process(pid, executable, background=False):
    import psutil
    try:
        process = psutil.Process(pid)
        if Path(process.exe()).resolve() != Path(executable).resolve(): return None
        if process.username() != psutil.Process().username(): return None
        if background and '--background' not in process.cmdline(): return None
        return process
    except (psutil.Error, OSError, ValueError): return None

def stop(root):
    # PIDs are checked against path and user before termination. Stop supervisor
    # before child to prevent a restart; never stop a different application.
    record = root / 'background-state.json'
    try: state = json.loads(record.read_text(encoding='utf-8'))
    except (OSError, ValueError): return
    for field, executable in (('supervisor', root / LAUNCHER), ('bridge', root / BRIDGE)):
        pid = state.get(field)
        if type(pid) is not int or pid == os.getpid(): continue
        process = owned_process(pid, executable, field == 'supervisor')
        if process:
            parent = owned_process(process.ppid(), executable, True) if field == 'supervisor' else None
            process.terminate(); process.wait(timeout=5)
            if parent: parent.wait(timeout=5)

def spawn(root):
    process = subprocess.Popen([str(root / LAUNCHER), '--background'], cwd=root,
        creationflags=subprocess.CREATE_NO_WINDOW)
    state_path = root / 'background-state.json'
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and process.poll() is None:
        try:
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if state.get('supervisor') == process.pid and type(state.get('bridge')) is int:
                return
        except (OSError, ValueError, AttributeError):
            pass
        time.sleep(0.1)
    if process.poll() is None:
        process.terminate()
    raise RuntimeError('后台未完成启动，请查看 logs/background.log')

def recovery_enabled(root):
    return registered() == run_command(root) and not (root / PAUSE_FILE).exists()

def request_stop(root):
    if root.is_dir():
        (root / PAUSE_FILE).touch()
        setup_logger(root).info('Background stop requested')
    stop(root)


def create_desktop_shortcut(root):
    """Use the current user's desktop; never replace an unrelated shortcut."""
    target = Path(root) / CONTROL
    if not target.is_file():
        return
    escaped = str(target).replace("'", "''")
    script = """$ErrorActionPreference='Stop'
$target='TARGET'
$shell=New-Object -ComObject WScript.Shell
$path=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Passport Music.lnk'
if (Test-Path -LiteralPath $path) {
 $old=$shell.CreateShortcut($path)
 if ($old.TargetPath -ne $target) { return }
}
$link=$shell.CreateShortcut($path)
$link.TargetPath=$target
$link.WorkingDirectory=Split-Path -LiteralPath $target
$link.IconLocation=$target+',0'
$link.Description='Passport Music'
$link.Save()
""".replace('TARGET', escaped)
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    shell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
    if result.returncode:
        raise RuntimeError('桌面快捷方式创建失败；可从安装目录打开 PassportMusicControl.exe。')

def install(source, start=True, destination=None):
    destination = Path(destination).resolve() if destination is not None else install_root()
    for name in (BRIDGE, LAUNCHER, '_internal'):
        if not (source / name).exists(): raise RuntimeError('Incomplete runtime: missing ' + name)
    # Check registry ownership before stopping/copying any installed files.
    previous = registered()
    if previous not in (None, run_command(destination)):
        raise RuntimeError('A different Passport autostart entry exists; it was preserved')
    request_stop(destination)
    if source.resolve() != destination.resolve():
        # Installed UI files can be locked during an upgrade; request its exit
        # first, then terminate only a matching, same-user process if needed.
        ui_state = destination / 'control-state.json'
        try:
            state = json.loads(ui_state.read_text(encoding='utf-8'))
            process = owned_process(state.get('pid'), destination / CONTROL)
        except (OSError, ValueError, TypeError):
            process = None
        if process:
            (destination / 'control-close-request').touch()
            try: process.wait(timeout=4)
            except Exception:
                process.terminate(); process.wait(timeout=5)
        shutil.copytree(source, destination, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('logs', '*-state.json', 'bridge-status.json', 'control-*-request*', '*.pid', PAUSE_FILE))
    set_autostart(destination, True)
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, INSTALL_KEY) as key:
        winreg.SetValueEx(key, 'InstallPath', 0, winreg.REG_SZ, str(destination))
    (destination / 'installation.json').write_text('{"schema":1,"installed":true}\n', encoding='utf-8')
    create_desktop_shortcut(destination)
    if not start:
        (destination / PAUSE_FILE).touch()
    try:
        configure_recovery_task(destination / LAUNCHER, True)
    finally:
        if start:
            spawn(destination)
    return destination

def setup_logger(root):
    logs = root / 'logs'; logs.mkdir(exist_ok=True)
    logger = logging.getLogger('passport.background')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(logs / 'background.log', maxBytes=2_097_152,
        backupCount=1, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    return logger

def supervise(root, recover=False):
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    api.CreateMutexW.restype = ctypes.c_void_p
    api.CloseHandle.argtypes = [ctypes.c_void_p]
    api.CloseHandle.restype = ctypes.c_bool
    handle = api.CreateMutexW(None, False, r'Local\FoloToy.PassportMusic.Background')
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        api.CloseHandle(handle); return
    logger = setup_logger(root)
    state_path = root / 'background-state.json'
    child = None
    try:
        if recover:
            if not recovery_enabled(root):
                return
            logger.info('Background supervisor recovered by scheduled task')
            # A terminated supervisor can leave its bridge child running.
            try:
                old = json.loads(state_path.read_text(encoding='utf-8'))
                pid = old.get('bridge')
                orphan = owned_process(pid, root / BRIDGE) if type(pid) is int else None
                if (orphan and orphan.ppid() == old.get('supervisor') and
                        orphan.create_time() <= state_path.stat().st_mtime):
                    orphan.terminate()
                    orphan.wait(timeout=5)
                    logger.info('Previous supervisor bridge process reclaimed')
            except FileNotFoundError:
                pass
            except (ValueError, AttributeError):
                logger.warning('Previous background process record is invalid')
        else:
            (root / PAUSE_FILE).unlink(missing_ok=True)
        delay = 5
        if (root / CONTROL).is_file():
            subprocess.Popen([str(root / CONTROL), '--tray'], cwd=root,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        while not (root / PAUSE_FILE).exists():
            env = dict(os.environ, PYTHONIOENCODING='utf-8')
            # No --launch-player. It may connect before or after NetEase opens.
            child = subprocess.Popen([str(root / BRIDGE)], cwd=root, env=env,
                creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            state_path.write_text(json.dumps(dict(supervisor=os.getpid(), bridge=child.pid))+'\n', encoding='utf-8')
            logger.info('Background bridge started; NetEase auto-launch disabled')
            def capture(stream):
                for line in stream:
                    logger.info('%s', decode_bridge_line(line).rstrip())
            reader = threading.Thread(target=capture, args=(child.stdout,), daemon=True)
            reader.start()
            started = time.monotonic()
            if (root / PAUSE_FILE).exists():
                child.terminate()
            code = child.wait(); reader.join(timeout=2); child.stdout.close()
            if (root / PAUSE_FILE).exists():
                return
            if time.monotonic()-started > 60: delay = 5
            logger.info('Bridge exited (%s); retry in %s seconds', code, delay)
            time.sleep(delay); delay = min(60, delay*2)
    except Exception:
        logger.exception('Background supervisor failed')
        raise
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
        api.CloseHandle(handle)

def notify(message, error=False):
    ctypes.windll.user32.MessageBoxW(None, message, 'Passport Music', 0x10 if error else 0x40)

def main():
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    for action in ('background', 'install', 'disable', 'stop', 'status'):
        actions.add_argument('--'+action, action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--no-start', action='store_true')
    parser.add_argument('--recover', action='store_true')
    parser.add_argument('--install-dir', type=Path)
    args = parser.parse_args()
    try:
        if args.background:
            root = own_root()
            if not args.recover or recovery_enabled(root):
                supervise(root, recover=args.recover)
            return
        if args.install:
            root = install(own_root(), not args.no_start, args.install_dir)
            message = '已启用登录自启和后台恢复。直接打开已配置的网易云即可。\n安装目录：'+str(root)
        elif args.disable:
            root = install_root(); set_autostart(root, False); request_stop(root)
            configure_recovery_task(root / LAUNCHER, False)
            message = '已取消开机自启并停止后台桥接。文件、配对与歌词微调值保留。'
        elif args.stop:
            request_stop(install_root()); message = '后台桥接已停止；下次登录仍会自动启动。'
        else:
            root = install_root()
            enabled = registered() == run_command(root)
            try: state = json.loads((root / 'background-state.json').read_text())
            except (OSError, ValueError): state = {}
            running = bool(owned_process(state.get('supervisor'), root / LAUNCHER, True)) if type(state.get('supervisor')) is int else False
            message = '登录自启：'+('已启用' if enabled else '未启用')+'\n后台进程：'+('运行中' if running else '未运行')+'\n日志目录：'+str(root / 'logs')
            try:
                result = subprocess.run([str(root / BRIDGE), '--diagnose'], cwd=root,
                    creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True,
                    text=True, encoding='utf-8', errors='replace', timeout=8,
                    env=dict(os.environ, PYTHONIOENCODING='utf-8'))
                status = json.loads(result.stdout.strip().splitlines()[-1])
                message += '\n网易云内部接口：'+('已连接' if status.get('internal_player') else '未连接，请打开网易云或检查快捷方式参数')
            except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
                message += '\n网易云接口检查未完成，请查看日志。'
        if not args.quiet: notify(message)
    except Exception as exc:
        if not args.quiet and not args.background:
            notify('操作失败：'+str(exc), True)
        raise SystemExit(1)

if __name__ == '__main__': main()
