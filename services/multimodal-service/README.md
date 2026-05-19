# Multimodal Service

`multimodal-service` 目前已经从纯骨架推进到“可本地推理”的第一阶段，但本轮只接入非 EEG 的 4 个模态：

- 文本情感
- 语音情感
- 面部情感
- 姿态情感

当前明确不包含：

- EEG 模态
- ASR 语音转写

## 当前能力

- PostgreSQL / SQLAlchemy / Alembic 基础骨架
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口
- 本地 ONNX 推理加载
- 兼容旧版 4 模态 API 路径

## 已实现接口

- `GET /health/live`
- `GET /health/ready`

### 推荐的新路径

- `POST /api/v1/non-eeg/text-emotion/infer`
- `POST /api/v1/non-eeg/audio-emotion/infer`
- `POST /api/v1/non-eeg/face-emotion/frame-infer`
- `POST /api/v1/non-eeg/pose-emotion/frame-infer`

### 兼容旧路径

- `POST /api/v1/text/infer`
- `POST /api/v1/audio/infer`
- `POST /api/v1/emotion-recognition/frame-infer`
- `POST /api/v1/pose/frame-infer`

## 模型目录

非 EEG 模型统一放在：

- `runtime-assets/models/text_emotion`
- `runtime-assets/models/audio_emotion`
- `runtime-assets/models/face_emotion`
- `runtime-assets/models/pose_emotion`

开发阶段推荐：

- 通过 Compose 把 `runtime-assets` 挂载到容器内 `/app/runtime-assets`
- `.onnx` 大文件通过 Git LFS 管理
- 镜像构建阶段不再把这 4 个大模型 bake 进镜像

## 关键环境变量

- `DATABASE_URL`
- `MINIO_ENDPOINT`
- `MULTIMODAL_BUCKET`
- `MODEL_PROVIDER`
- `POSE_WINDOW`

## 当前 Step 4D 已完成

- `audio-turns` 后内部补齐 `speech_emotion` / `text_emotion`
- `captures/face` / `captures/pose` 的连续采样接入
- `/live` 的前端看板稳定结构
- `/turns/{turn_id}/bundle` 的 turn 级聚合输出

## 下一步尚未完成

- EEG 模态
- Dolphin ASR
- MinIO 音频落盘
- 和 `consultation-service`、`risk-service` 的正式联调
