# EEG Bridge Service

`services/eeg-bridge` 是 Jetson / Linux 使用的容器化 EEG bridge。

它复用 `tools/eeg-tools/bridge-runtime` 的 BLE 采集与 Redis Stream 写入逻辑，并通过单独的 Compose 文件显式启用：

- `infra/compose/docker-compose.jetson-eeg-bridge.yml`

## 当前定位

- 这是 Jetson / Linux 专用能力
- Windows 默认开发阶段不要启动它
- Windows 默认开发阶段只保留：
  - Docker 内唯一一份 `multimodal-service`
  - 宿主机 `scripts/start_eeg_tools.ps1`

## 启用方式

启动前先确认根 `.env` 已启用 EEG：

```env
MCS_CONTAINER_EEG_ENABLED=true
MCS_CONTAINER_EEG_PROVIDER=redis_stream
MCS_CONTAINER_EEG_AUTO_START_TRANSPORT=true
MCS_CONTAINER_EEG_REQUIRE_TRANSPORT_FOR_READY=true
```

Linux / Jetson 启动：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build eeg-bridge multimodal-service
```

也可以使用仓库快捷命令：

```bash
make eeg-up
make eeg-logs
```

如果 `multimodal-service` 需要 GPU / Nvidia runtime：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build eeg-bridge multimodal-service
```

## 运行前提

- 仅建议在 Linux / Jetson 主机使用
- 主机侧需要可工作的 BlueZ / D-Bus / 蓝牙能力
- Compose 会挂载 `/run/dbus/system_bus_socket`
- Compose 会启用 `network_mode: host` 和 `privileged: true`
- 主机 Redis 端口必须与 `REDIS_PORT` 一致，默认是 `6379`
- 同一时间不能再运行 Windows bridge、宿主机 Python bridge 或 replay

启动前可检查：

```bash
systemctl is-active bluetooth
rfkill list bluetooth
bluetoothctl show
bluetoothctl scan on
```

容器启动时会检查 system D-Bus socket。缺失或挂载错误时进程会输出明确错误并退出。
Docker 健康检查只判断 bridge 进程状态；设备暂时关闭导致的 `scanning` 或
`disconnected` 不会被当作容器死亡。

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
- `EEG_HOST_BRIDGE_SOURCE=windows_host_bridge`
- `EEG_HOST_BRIDGE_PAYLOAD_ENCODING=hex`

后两个值用于保持现有 Redis Stream 协议不变。不要在容器化期间修改 Stream key、
Entry 字段、payload 编码或批处理参数。

完整设计及验收要求见：

- `docs/architecture/eeg-bridge-containerization-design_20260826.md`
