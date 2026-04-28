@echo off
setlocal
set "TARGET=%LOCALAPPDATA%\MQTTSubscriptionManager"
if not exist "%TARGET%" mkdir "%TARGET%"
if exist "%TARGET%\data\mqtt_manager.db" copy /y "%TARGET%\data\mqtt_manager.db" "%TEMP%\mqtt_manager_backup.db" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%~dp0mqtt-subscription-manager.zip' -DestinationPath '%TARGET%' -Force"
if exist "%TEMP%\mqtt_manager_backup.db" (
  if not exist "%TARGET%\data" mkdir "%TARGET%\data"
  copy /y "%TEMP%\mqtt_manager_backup.db" "%TARGET%\data\mqtt_manager.db" >nul
  del /f /q "%TEMP%\mqtt_manager_backup.db" >nul 2>nul
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $programs = [Environment]::GetFolderPath('Programs'); $desktopShortcut = $shell.CreateShortcut((Join-Path $desktop 'MQTT Subscription Manager.lnk')); $desktopShortcut.TargetPath = (Join-Path '%TARGET%' 'start_mqtt_manager.bat'); $desktopShortcut.WorkingDirectory = '%TARGET%'; $desktopShortcut.Save(); $menuShortcut = $shell.CreateShortcut((Join-Path $programs 'MQTT Subscription Manager.lnk')); $menuShortcut.TargetPath = (Join-Path '%TARGET%' 'start_mqtt_manager.bat'); $menuShortcut.WorkingDirectory = '%TARGET%'; $menuShortcut.Save()"
start "" "%TARGET%\start_mqtt_manager.bat"
echo Install complete. Target=%TARGET%
