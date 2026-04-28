$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$python = Join-Path $root '.venv\Scripts\python.exe'
$pyinstaller = Join-Path $root '.venv\Scripts\pyinstaller.exe'
$frontendDir = Join-Path $root 'frontend'
$backendDir = Join-Path $root 'backend'
$releaseRoot = Join-Path $root 'release\windows'
$portableDir = Join-Path $releaseRoot 'portable'
$buildRoot = Join-Path $releaseRoot 'build'
$installerWork = Join-Path $buildRoot 'installer'
$zipPath = Join-Path $releaseRoot 'mqtt-subscription-manager.zip'
$setupPath = Join-Path $releaseRoot 'Setup_MQTTSubscriptionManager.exe'
$manualPath = Join-Path $root 'WINDOWS_USER_GUIDE.md'
$pyinstallerWork = Join-Path $buildRoot 'pyinstaller-work'
$pyinstallerSpec = Join-Path $buildRoot 'spec'

if (-not (Test-Path $python)) {
    throw 'Workspace .venv not found.'
}

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
Remove-Item $portableDir, $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $portableDir, $buildRoot, $installerWork -Force | Out-Null

Push-Location $frontendDir
npm run build
Pop-Location

& $python -m pip install pyinstaller

$pyinstallerArgs = @(
    '--noconfirm',
    '--clean',
    '--onefile',
    '--name', 'MQTTSubscriptionManager',
    '--distpath', $portableDir,
    '--workpath', $pyinstallerWork,
    '--specpath', $pyinstallerSpec,
    '--add-data', "$frontendDir\dist;frontend\dist",
    "$backendDir\desktop_launcher.py"
)
& $pyinstaller @pyinstallerArgs

New-Item -ItemType Directory -Path (Join-Path $portableDir 'data') -Force | Out-Null
Copy-Item (Join-Path $backendDir 'data\mqtt_manager.db') (Join-Path $portableDir 'data\mqtt_manager.db') -Force
Copy-Item $manualPath (Join-Path $portableDir 'WINDOWS_USER_GUIDE.md') -Force

$startBat = @(
    '@echo off',
    'setlocal',
    'cd /d %~dp0',
    'start "" "%~dp0MQTTSubscriptionManager.exe"'
) -join "`r`n"
Set-Content -Path (Join-Path $portableDir 'start_mqtt_manager.bat') -Value $startBat -Encoding ASCII

$uninstallBat = @(
    '@echo off',
    'setlocal',
    'set "TARGET=%LOCALAPPDATA%\MQTTSubscriptionManager"',
    'taskkill /IM MQTTSubscriptionManager.exe /F >nul 2>nul',
    'timeout /t 1 /nobreak >nul',
    'if exist "%TARGET%" rd /s /q "%TARGET%"',
    'echo MQTT Subscription Manager removed.'
) -join "`r`n"
Set-Content -Path (Join-Path $portableDir 'uninstall_mqtt_manager.bat') -Value $uninstallBat -Encoding ASCII

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
Compress-Archive -Path (Join-Path $portableDir '*') -DestinationPath $zipPath -Force

$installBat = @(
    '@echo off',
    'setlocal',
    'set "TARGET=%LOCALAPPDATA%\MQTTSubscriptionManager"',
    'if not exist "%TARGET%" mkdir "%TARGET%"',
    'if exist "%TARGET%\data\mqtt_manager.db" copy /y "%TARGET%\data\mqtt_manager.db" "%TEMP%\mqtt_manager_backup.db" >nul',
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''%~dp0mqtt-subscription-manager.zip'' -DestinationPath ''%TARGET%'' -Force"',
    'if exist "%TEMP%\mqtt_manager_backup.db" (',
    '  if not exist "%TARGET%\data" mkdir "%TARGET%\data"',
    '  copy /y "%TEMP%\mqtt_manager_backup.db" "%TARGET%\data\mqtt_manager.db" >nul',
    '  del /f /q "%TEMP%\mqtt_manager_backup.db" >nul 2>nul',
    ')',
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath(''Desktop''); $programs = [Environment]::GetFolderPath(''Programs''); $desktopShortcut = $shell.CreateShortcut((Join-Path $desktop ''MQTT Subscription Manager.lnk'')); $desktopShortcut.TargetPath = (Join-Path ''%TARGET%'' ''start_mqtt_manager.bat''); $desktopShortcut.WorkingDirectory = ''%TARGET%''; $desktopShortcut.Save(); $menuShortcut = $shell.CreateShortcut((Join-Path $programs ''MQTT Subscription Manager.lnk'')); $menuShortcut.TargetPath = (Join-Path ''%TARGET%'' ''start_mqtt_manager.bat''); $menuShortcut.WorkingDirectory = ''%TARGET%''; $menuShortcut.Save()"',
    'start "" "%TARGET%\start_mqtt_manager.bat"',
    'echo Install complete. Target=%TARGET%'
) -join "`r`n"
Set-Content -Path (Join-Path $installerWork 'install.bat') -Value $installBat -Encoding ASCII

Copy-Item $zipPath (Join-Path $installerWork 'mqtt-subscription-manager.zip') -Force

$sedContent = @(
    '[Version]',
    'Class=IEXPRESS',
    'SEDVersion=3',
    '',
    '[Options]',
    'PackagePurpose=InstallApp',
    'ShowInstallProgramWindow=1',
    'HideExtractAnimation=0',
    'UseLongFileName=1',
    'InsideCompressed=0',
    'CAB_FixedSize=0',
    'CAB_ResvCodeSigning=0',
    'RebootMode=I',
    'InstallPrompt=',
    'DisplayLicense=',
    'FinishMessage=MQTT Subscription Manager installation complete.',
    "TargetName=$setupPath",
    'FriendlyName=MQTT Subscription Manager Setup',
    'AppLaunched=install.bat',
    'PostInstallCmd=<None>',
    'AdminQuietInstCmd=',
    'UserQuietInstCmd=',
    'SourceFiles=SourceFiles',
    '',
    '[SourceFiles]',
    "SourceFiles0=$installerWork",
    '',
    '[SourceFiles0]',
    'mqtt-subscription-manager.zip=',
    'install.bat='
) -join "`r`n"
Set-Content -Path (Join-Path $installerWork 'mqtt-subscription-manager.sed') -Value $sedContent -Encoding ASCII

Push-Location $installerWork
Start-Process -FilePath "$env:WINDIR\System32\iexpress.exe" -ArgumentList '/N', 'mqtt-subscription-manager.sed' -Wait -NoNewWindow
Pop-Location

Write-Host "Portable package: $portableDir"
Write-Host "Installer: $setupPath"