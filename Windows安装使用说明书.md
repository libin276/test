# MQTT订阅管理器 Windows 安装使用说明书

## 1. 交付内容

- 安装包：release/windows/Setup_MQTTSubscriptionManager.exe
- 便携版目录：release/windows/portable
- 数据库文件：release/windows/portable/data/mqtt_manager.db

## 2. 安装方式

1. 双击运行 Setup_MQTTSubscriptionManager.exe。
2. 安装程序会将文件释放到 %LOCALAPPDATA%/MQTTSubscriptionManager。
3. 安装完成后会自动创建桌面快捷方式和开始菜单快捷方式。
4. 安装结束后程序会自动启动，并在默认浏览器打开管理界面。

## 3. 启动与停止

- 双击桌面上的 MQTT订阅管理器 快捷方式即可启动。
- 程序默认监听 http://127.0.0.1:9527。
- 如需关闭程序，可在任务管理器中结束 MQTTSubscriptionManager.exe，或直接关闭命令窗口。

## 4. 数据目录

- 程序运行数据默认存放在 %LOCALAPPDATA%/MQTTSubscriptionManager/data。
- SQLite 数据库文件名为 mqtt_manager.db。
- 建议定期备份 data 目录，避免联调数据丢失。

## 5. 升级方式

1. 关闭当前运行中的 MQTT订阅管理器。
2. 重新运行新的 Setup_MQTTSubscriptionManager.exe。
3. 安装程序会覆盖程序文件，但会保留 data 目录中的数据库。

## 6. 卸载方式

1. 进入 %LOCALAPPDATA%/MQTTSubscriptionManager。
2. 运行 uninstall_mqtt_manager.bat。
3. 如需彻底清理，可手动删除桌面快捷方式和开始菜单中的 MQTT订阅管理器。

## 7. 开发侧重新打包命令

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_package.ps1
```

执行完成后将在 release/windows 下生成最新的便携版和安装包。