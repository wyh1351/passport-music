param([string]$Python = 'python', [string]$Output = 'build/windows')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    & $Python -m PyInstaller --noconfirm --clean --onedir --console --name PassportMusic `
        --distpath $Output --workpath build/pyinstaller --specpath build `
        --collect-all bleak --collect-all winrt --collect-all comtypes --collect-all websockets `
        companion/passport_music.py
    if ($LASTEXITCODE -ne 0) { throw 'Bridge packaging failed' }
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name PassportMusicBackground `
        --distpath build/background-launcher --workpath build/pyinstaller-background --specpath build `
        companion/background_music.py
    if ($LASTEXITCODE -ne 0) { throw 'Background launcher packaging failed' }
    $runtime = Join-Path $Output 'PassportMusic'
    Copy-Item -LiteralPath 'build/background-launcher/PassportMusicBackground.exe' -Destination $runtime -Force
    Copy-Item -LiteralPath 'companion/Open-NetEase-Remote.cmd' -Destination $runtime -Force
    foreach ($entry in @(@('Enable-Autostart.cmd','install'),@('Disable-Autostart.cmd','disable'),@('Stop-Background.cmd','stop'),@('Background-Status.cmd','status'))) {
        $body = '@echo off' + "`r`n" + 'start "" "%~dp0PassportMusicBackground.exe" --' + $entry[1] + "`r`n"
        [System.IO.File]::WriteAllText((Join-Path $runtime $entry[0]),$body,[System.Text.Encoding]::ASCII)
    }
} finally { Pop-Location }
