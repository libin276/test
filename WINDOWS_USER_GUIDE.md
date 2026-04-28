# MQTT订阅管理器 Windows 使用说明书

## 1. 交付物

- 安装包：release/windows/Setup_MQTTSubscriptionManager.exe
- 便携版：release/windows/portable
- 本地数据库：release/windows/portable/data/mqtt_manager.db

## 2. 安装步骤

1. 双击运行 Setup_MQTTSubscriptionManager.exe。
2. 程序会安装到 %LOCALAPPDATA%/MQTTSubscriptionManager。
3. 安装完成后会自动创建桌面和开始菜单快捷方式。
4. 安装程序会自动启动 MQTT订阅管理器，并在默认浏览器中打开界面。

## 3. 运行方式

- 双击桌面快捷方式 MQTT Subscription Manager。
- 程序默认监听 http://127.0.0.1:9527。
- 如需关闭程序，可关闭运行窗口或在任务管理器中结束 MQTTSubscriptionManager.exe。

## 4. 数据说明

- SQLite 数据默认保存在 %LOCALAPPDATA%/MQTTSubscriptionManager/data/mqtt_manager.db。
- 再次安装新版本时，安装程序会保留已有数据库文件。
- 建议定期备份 data 目录。

## 5. 卸载方式

1. 进入 %LOCALAPPDATA%/MQTTSubscriptionManager。
2. 运行 uninstall_mqtt_manager.bat。
3. 如需彻底清理，可手动删除桌面和开始菜单快捷方式。

## 6. 重新打包命令

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_package.ps1
```

执行完成后会在 release/windows 目录生成最新安装包和便携版。