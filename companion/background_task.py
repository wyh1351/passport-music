"""Register the current user's windowless Passport Music recovery task."""
import csv
from datetime import datetime, timedelta
import locale
import os
from pathlib import Path
import re
import subprocess
import tempfile
from xml.etree import ElementTree
from xml.sax.saxutils import escape


TASK_NS = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
RECOVERY_ARGS = '--background --recover --quiet'


def windows_tool(name, *args):
    executable = Path(os.environ['SystemRoot']) / 'System32' / (name + '.exe')
    return subprocess.run([str(executable), *args], capture_output=True,
                          creationflags=subprocess.CREATE_NO_WINDOW, timeout=25)


def current_user_sid():
    result = windows_tool('whoami', '/user', '/fo', 'csv', '/nh')
    result.check_returncode()
    row = next(csv.reader(result.stdout.decode(locale.getencoding(), errors='replace').strip().splitlines()))
    sid = row[1]
    if not re.fullmatch(r'S-1-\d+(?:-\d+)+', sid):
        raise RuntimeError('无法识别当前 Windows 用户')
    return sid


def task_definition(launcher, sid):
    start = (datetime.now() + timedelta(minutes=1)).isoformat(timespec='seconds')
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="{TASK_NS['t']}">
  <RegistrationInfo><Description>Restore the Passport Music bridge after an unexpected exit.</Description></RegistrationInfo>
  <Triggers><TimeTrigger>
    <Repetition><Interval>PT1M</Interval></Repetition>
    <StartBoundary>{start}</StartBoundary><Enabled>true</Enabled>
  </TimeTrigger></Triggers>
  <Principals><Principal id="PassportMusic">
    <UserId>{sid}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel>
  </Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions Context="PassportMusic"><Exec>
    <Command>{escape(str(launcher))}</Command><Arguments>{RECOVERY_ARGS}</Arguments>
    <WorkingDirectory>{escape(str(launcher.parent))}</WorkingDirectory>
  </Exec></Actions>
</Task>'''


def owns_task(xml, launcher, sid):
    # schtasks can emit console-encoded bytes with a UTF-16 XML declaration.
    if xml.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = xml.decode('utf-16')
    else:
        try:
            text = xml.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = xml.decode(locale.getencoding())
    task = ElementTree.fromstring(text)
    actions = task.findall('t:Actions/*', TASK_NS)
    if len(actions) != 1 or actions[0].tag != f'{{{TASK_NS["t"]}}}Exec':
        return False
    command = actions[0].findtext('t:Command', default='', namespaces=TASK_NS)
    arguments = actions[0].findtext('t:Arguments', default='', namespaces=TASK_NS)
    owner = task.findtext('t:Principals/t:Principal/t:UserId', namespaces=TASK_NS)
    return Path(command) == launcher and arguments == RECOVERY_ARGS and owner == sid


def configure_recovery_task(launcher, enabled):
    sid = current_user_sid()
    name = 'FoloToyPassportMusicRecovery-' + sid
    existing = windows_tool('schtasks', '/Query', '/TN', name, '/XML')
    exists = existing.returncode == 0
    if exists and not owns_task(existing.stdout, launcher, sid):
        raise RuntimeError('同名恢复任务属于其他安装，请检查任务计划程序')
    if enabled:
        # schtasks opens the XML itself, so close the file before launching it.
        with tempfile.TemporaryDirectory() as directory:
            xml = Path(directory) / 'recovery.xml'
            xml.write_text(task_definition(launcher, sid), encoding='utf-16')
            args = ['/Create', '/TN', name, '/XML', str(xml)]
            if exists:
                args.append('/F')
            result = windows_tool('schtasks', *args)
    elif exists:
        result = windows_tool('schtasks', '/Delete', '/TN', name, '/F')
    else:
        return
    if result.returncode:
        detail = result.stderr.decode(locale.getencoding(), errors='replace').strip()
        raise RuntimeError('后台恢复任务配置失败。' + detail)
