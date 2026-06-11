# Multimodal Service

`multimodal-service` 是当前项目中的多模态采集、推理、热态与对象存储编排服务。

当前仓库里的实现已经不再只是“非 EEG 四模态骨架”。现状更准确地说是：

- 已接入文本情感
- 已接入语音情感
- 已接入面部情感
- 已接入姿态情感
- 已接入 ASR 运行时
- 已接入 EEG turn 级运行时、Redis 热态、MinIO 原始文件与结果落库主链

## 当前边界

当前代码里已经存在 EEG 与 ASR 相关能力，但团队当前冻结的 Windows 开发边界是：

- Docker 内保留唯一一份业务侧 `multimodal-service`
- 不把整份 `multimodal-service` 作为默认链路搬到 Windows 宿主机
- EEG transport 统一走“宿主机 `eeg-tools` -> Redis Stream -> Docker 内 multimodal-service”

## Windows 默认开发链路

截至 `2026-06-09`，Windows 开发阶段的默认 EEG 链路已经固定为：

```text
Docker Compose
  -> gateway / consultation / assessment / risk
  -> container multimodal-service (唯一一份)

Windows host
  -> eeg-tools
  -> Redis Stream
  -> container multimodal-service
```

默认做法：

1. 启动 Docker 主链：
   `docker compose -f infra/compose/docker-compose.dev.yml up -d --build`
2. 真机联调时启动：
   `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge`
3. 无设备联调时启动：
   `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode simulate`

不要做的事：

- 不要在默认开发链路里设置 `MCS_MULTIMODAL_SERVICE_URL`
- 不要为了 EEG 默认再起一份宿主机完整 `multimodal-service`

详细方案见：

- [docs/architecture/eeg-pure-docker-single-command-plan_20260607.md](/e:/DataSets/Projects/depression-system/docs/architecture/eeg-pure-docker-single-command-plan_20260607.md)

## 当前能力

- PostgreSQL / SQLAlchemy / Alembic
- Redis live state
- MinIO 对象存储
- 本地 ONNX 推理加载
- Dolphin ASR 运行时
- EEG turn start / finish / results API
- `/live` 与 `/live/stream` 多模态实时看板输出
- 兼容旧版部分非 EEG API 路径

## 主要接口

- `GET /health/live`
- `GET /health/ready`
- `POST /api/v1/multimodal/sessions`
- `POST /api/v1/multimodal/sessions/{session_id}/warmup`
- `POST /api/v1/multimodal/sessions/{session_id}/audio-turns`
- `POST /api/v1/multimodal/sessions/{session_id}/visual-captures`
- `POST /api/v1/multimodal/sessions/{session_id}/eeg/turns/start`
- `POST /api/v1/multimodal/sessions/{session_id}/eeg/turns/{turn_id}/finish`
- `GET /api/v1/multimodal/sessions/{session_id}/eeg/turns/{turn_id}/results`

## 运行配置

当前服务通过环境变量读取配置，主要来自：

- Docker Compose 注入
- 仓库根 `.env`
- 服务级 `.env.example`

推荐约定是：

- 真实开发值放根 `.env`
- 模板说明放 `.env.example`
- Compose 只负责编排和引用变量
- `app/config.py` 只做解析与兜底

`multimodal-service` 自身已有示例配置文件：

- `.env.example`

## 关键环境变量

- `DATABASE_URL`
- `REDIS_ENABLED`
- `REDIS_URL`
- `REDIS_KEY_PREFIX`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MULTIMODAL_BUCKET`
- `MODEL_PROVIDERS`
- `ASR_DEVICE`
- `EEG_ENABLED`
- `EEG_PROVIDER`
- `EEG_AUTO_START_TRANSPORT`
- `EEG_REQUIRE_TRANSPORT_FOR_READY`
- `EEG_DEVICE_NAME_HINT`
- `EEG_NOTIFY_CHAR_UUID`
- `EEG_STREAM_KEY_PREFIX`
- `EEG_STREAM_CONSUMER_GROUP`
- `EEG_CHANNEL_NAMES`
- `EEG_SAMPLING_RATE`
- `EEG_WINDOW_SECONDS`
- `EEG_MODEL_PATH`

## 模型与资源目录

- 非 EEG 模型：`runtime-assets/models/*`
- ASR 资源：`runtime-assets/asr/*`
- EEG 资源：`runtime-assets/eeg/*`

开发阶段通常通过 Compose 把 `runtime-assets` 挂载到容器内 `/app/runtime-assets`。

## 验证

如果本机 Python 环境完整，可以从仓库根目录执行相关测试或类型检查。

当前更建议优先通过：

- `docker compose config`
- 服务级测试
- `/health/ready`
- `/live` / `/live/stream`

来做联调验证。
