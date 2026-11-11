"""Build a clean Windows control-center folder; never package local settings."""
from pathlib import Path
import argparse
import shutil
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('dist/PassportMusic'))
    parser.add_argument('--work-dir',type=Path,help='Optional short temporary parent path on Windows')
    args=parser.parse_args()
    if sys.platform!='win32':raise SystemExit('Run this builder on Windows.')
    repo=Path(__file__).resolve().parents[1]
    output=args.output.resolve()
    if output.exists():raise SystemExit('Choose a new output folder; existing files were preserved.')
    sys.path.insert(0,str(repo/'companion'))
    from control_brand import app_image
    from PyInstaller.__main__ import run
    with tempfile.TemporaryDirectory(prefix='pm-',dir=args.work_dir) as directory:
        root=Path(directory)
        icon=root/'passport-music.ico'
        app_image(256).save(icon,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
        manifest=root/'control.manifest'
        manifest.write_text('''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
 <assemblyIdentity version="1.0.0.0" processorArchitecture="*" name="FoloToy.PassportMusic.ControlCenter" type="win32"/>
 <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges><requestedExecutionLevel level="asInvoker" uiAccess="false"/></requestedPrivileges></security></trustInfo>
 <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>
  <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
  <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
 </windowsSettings></application>
</assembly>
''',encoding='utf-8')
        programs=(('PassportMusic','passport_music.py','_internal',True),
                  ('PassportMusicBackground','background_music.py','_background',False),
                  ('PassportMusicControl','control_center.py','_control',False))
        for name,source,contents,console in programs:
            command=['--noconfirm','--onedir','--console' if console else '--windowed',
                     '--name',name,'--contents-directory',contents,'--icon',str(icon),
                     '--workpath',str(root/'build'/name),'--specpath',str(root/'spec'),
                     '--distpath',str(root/'dist')]
            if name!='PassportMusicBackground':
                for package in ('bleak','winrt','comtypes','websockets'):
                    command.extend(['--collect-all',package])
            if name=='PassportMusicControl':command.extend(['--manifest',str(manifest)])
            run(command+[str(repo/'companion'/source)])
        output.mkdir(parents=True)
        for name,_,_,_ in programs:shutil.copytree(root/'dist'/name,output,dirs_exist_ok=True)
    for source in (repo/'companion').glob('*.cmd'):shutil.copy2(source,output/source.name)
    legacy={'Enable-Autostart.cmd':'--install','Disable-Autostart.cmd':'--disable',
            'Stop-Background.cmd':'--stop','Background-Status.cmd':'--status'}
    for name,action in legacy.items():
        (output/name).write_text('@echo off\nstart "" "%~dp0PassportMusicBackground.exe" '+action+'\n',encoding='ascii')
    (output/'Start-Bluetooth.cmd').write_text('@echo off\n"%~dp0PassportMusic.exe"\npause\n',encoding='ascii')
    shutil.copy2(repo/'LICENSE',output/'Passport-MIT-LICENSE.txt')
    for suffix in ('','.zh_CN'):shutil.copy2(repo/f'docs/netease-music{suffix}.md',output/f'README{suffix}.md')
    assert not (output/'desktop-port.txt').exists()
    print('Clean Windows build:',output)


if __name__=='__main__':main()
