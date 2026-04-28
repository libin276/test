@echo off
setlocal
set "TARGET=%LOCALAPPDATA%\MQTTSubscriptionManager"
taskkill /IM MQTTSubscriptionManager.exe /F >nul 2>nul
timeout /t 1 /nobreak >nul
if exist "%TARGET%" rd /s /q "%TARGET%"
echo MQTT Subscription Manager removed.
