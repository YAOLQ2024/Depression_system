# EEG Bridge Service

`services/eeg-bridge` 是 Jetson / Linux 阶段预留的容器化 EEG bridge。

它复用 `tools/eeg-tools/bridge-runtime` 的 BLE 采集与 Redis Stream 写入逻辑，并通过单独的 Compose 文件显式启用：

- `infra/compose/docker-compose.jetson-eeg-bridge.yml`

## 当前定位

- 这是 Jetson / Linux 专用能力
- Windows 默认开发阶段不要启动它
- Windows 默认开发阶段只保留：
  - Docker 内唯一一份 `multimodal-service`
  - 宿主机 `scripts/start_eeg_tools.ps1`

## 启用方式

```powershell
docker compose `
  -f infra/compose/docker-compose.dev.yml `
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml `
  up -d --build eeg-bridge multimodal-service
```

如果届时 `multimodal-service` 还需要 GPU / Nvidia runtime，可以再叠加：

```powershell
docker compose `
  -f infra/compose/docker-compose.dev.yml `
  -f infra/compose/docker-compose.gpu.yml `
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml `
  up -d --build eeg-bridge multimodal-service
```

## 运行前提

- 仅建议在 Linux / Jetson 主机使用
- 主机侧需要可工作的 BlueZ / D-Bus / 蓝牙能力
- Compose 会挂载 `/run/dbus/system_bus_socket`
- Compose 会启用 `network_mode: host` 和 `privileged: true`

## 环境变量

该服务使用与 `tools/eeg-tools/.env.example` 相同的一组 EEG bridge 变量，例如：

- `REDIS_URL`
- `EEG_STREAM_KEY_PREFIX`
- `EEG_DEVICE_NAME_HINT`
- `EEG_NOTIFY_CHAR_UUID`
- `EEG_SCAN_SECONDS`
- `EEG_RECONNECT_DELAY_SECONDS`
- `EEG_HOST_BRIDGE_RECORD_ENABLED`

额外约定：

- `EEG_HOST_BRIDGE_APP_NAME=eeg-bridge`
- `EEG_HOST_BRIDGE_SOURCE=jetson_eeg_bridge`
