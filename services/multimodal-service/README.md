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

- `app/models/non_eeg/text_emotion`
- `app/models/non_eeg/audio_emotion`
- `app/models/non_eeg/face_emotion`
- `app/models/non_eeg/pose_emotion`

`.onnx` 大文件建议使用 Git LFS 管理。

## 关键环境变量

- `DATABASE_URL`
- `MINIO_ENDPOINT`
- `MULTIMODAL_BUCKET`
- `MODEL_PROVIDER`
- `POSE_WINDOW`

## 下一步尚未完成

- 会话级多模态采集接口
- 每个问诊 turn 的标准化 bundle 落库
- 面向前端面板的 live / history 查询接口
- 和 `consultation-service`、`risk-service` 的正式联调
