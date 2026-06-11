# EEG 单入口与纯业务容器边界

更新时间：2026-06-09

## 1. 当前结论

EEG 改造已经收口到一条固定链路：

```text
Windows host
  -> tools/eeg-tools
  -> bridge 或 replay
  -> Redis Stream

Docker Compose
  -> 唯一一份 multimodal-service
  -> consultation / assessment / risk / gateway
```

这意味着：

- 宿主机不再启动完整 `multimodal-service`
- 业务侧只保留 Docker 内唯一一份 `multimodal-service`
- Windows 阶段的宿主机能力只剩 `tools/eeg-tools`

## 2. 唯一正式入口

当前 EEG 宿主机工具只保留：

- `scripts/start_eeg_tools.ps1`
- `scripts/build_eeg_tools_exe.ps1`
- `tools/eeg-tools/`

补充：`scripts/build_eeg_bridge_exe.ps1` 也保留，用于快速构建单体 bridge-only EXE（输出到仓库根 `eeg-bridge.exe`），方便在无 Python 环境的机器上直接跑蓝牙采集。它不是正式入口，仅作为统一 `eeg-tools` EXE 之外的快捷构建路径。

`tools/eeg-tools` 内部包含两类 runtime：

- `bridge-runtime`
  真实蓝牙 EEG 设备采集并写入 Redis Stream
- `replay-runtime`
  回放录制文件或生成模拟 EEG 流量并写入 Redis Stream

外部不再暴露独立的 `eeg-host-bridge` / `eeg-replay` 工具目录与启动脚本。

## 3. 配置约定

配置分工固定如下：

- 仓库根 `.env`
  放跨服务共享变量，例如 `REDIS_URL`、`EEG_STREAM_KEY_PREFIX`
- `tools/eeg-tools/.env.example`
  放 EEG 宿主机工具模板
- `infra/compose/*.yml`
  只负责编排、注入和引用变量，不再硬编码宿主机多模态地址

源码运行时，`tools/eeg-tools` 会读取：

1. 仓库根 `.env`
2. `tools/eeg-tools/.env`

EXE 运行时，会读取：

1. EXE 同级目录 `.env`

不再保留分散的子工具专属配置文件。

## 4. 默认开发命令

启动业务主链：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

真实设备：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge
```

模拟联调：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode simulate
```

真实录制文件回放：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 `
  -Command replay `
  -Mode raw `
  -ReplayFile <jsonl路径> `
  -Speed 1.0
```

## 5. Docker 边界

`infra/compose/docker-compose.dev.yml` 的默认约束是：

- `consultation-service`
- `assessment-service`
- `risk-service`
- `gateway-service`

全部固定访问：

`http://multimodal-service:8000`

因此不再允许把默认开发链路切到宿主机多模态地址。

也不再保留任何“宿主机完整多模态服务”启动方式。

## 6. Jetson 预留能力

Jetson / Linux 阶段仍预留单独 bridge 容器：

- `infra/compose/docker-compose.jetson-eeg-bridge.yml`
- `services/eeg-bridge/`

它复用 `tools/eeg-tools/bridge-runtime` 代码，但默认不加入 Windows 开发链路。

只有在 Jetson / Linux 主机上才显式叠加：

```powershell
docker compose `
  -f infra/compose/docker-compose.dev.yml `
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml `
  up -d --build eeg-bridge multimodal-service
```

## 7. 已清理的内容

这次收口后，以下内容应视为已退役并删除：

- 宿主机完整 `multimodal-service` 启动方式
- 分散的 bridge / replay 子工具入口
- 分散的 bridge / replay 子工具目录
- 旧的 build / dist / cache / pycache 中间产物

## 8. 最终目标

当前阶段的最终形态不是“Windows 下纯 Docker 直接连蓝牙”，而是：

- Docker 内只跑业务服务
- Windows 宿主机只跑一个统一 EEG 工具入口
- 后续迁移到 Jetson 时，再把 bridge 容器显式打开

这条边界已经固定，不再保留旧链路兼容层。
