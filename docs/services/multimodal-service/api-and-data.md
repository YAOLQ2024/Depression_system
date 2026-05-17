# `multimodal-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已实现 |
| `/health/ready` | `GET` | 就绪检查 | 已实现 |
| `/api/v1/multimodal/sessions` | `POST` | 创建多模态采集会话 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}` | `GET` | 获取会话状态 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}/warmup` | `POST` | 预热非 EEG 模型运行时 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}/audio-turns` | `POST` | 提交音频情感与可选文本情感 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}/captures/face` | `POST` | 提交表情采集片段 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}/captures/pose` | `POST` | 提交姿态采集片段 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}/live` | `GET` | 获取会话级最新 live 结果 | 已实现（非 EEG） |
| `/api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle` | `GET` | 获取 turn 级多模态 bundle | 已实现（非 EEG） |
| `/api/v1/text/infer` | `POST` | 兼容原独立文本推理接口 | 已实现（兼容路径） |
| `/api/v1/audio/infer` | `POST` | 兼容原独立语音情感接口 | 已实现（兼容路径） |
| `/api/v1/emotion-recognition/frame-infer` | `POST` | 兼容原独立面部情感接口 | 已实现（兼容路径） |
| `/api/v1/pose/frame-infer` | `POST` | 兼容原独立姿态情感接口 | 已实现（兼容路径） |
| `/api/v1/multimodal/sessions/{session_id}/captures/eeg` | `POST` | 提交脑电采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/transcriptions` | `POST` | 语音转写 | 不在当前阶段（ASR 不接入） |

## 2. 核心实体

### 2.1 multimodal_session

- `session_id`
- `owner_session_id`
- `user_id`
- `status`
- `enabled_modalities`
- `latest_live_payload`
- `session_summary_payload`
- `notes`
- `warmed_up_at`
- `completed_at`
- `created_at`
- `updated_at`

### 2.2 multimodal_capture

- `capture_id`
- `session_id`
- `consultation_turn_id`
- `modality`
- `capture_kind`
- `source_ref_id`
- `storage_uri`
- `capture_payload`
- `captured_at`
- `created_at`

### 2.3 multimodal_inference_result

- `result_id`
- `session_id`
- `consultation_turn_id`
- `modality`
- `source_kind`
- `source_ref_id`
- `inference_payload`
- `captured_at`
- `created_at`

### 2.4 multimodal_turn_bundle

- `bundle_id`
- `session_id`
- `consultation_turn_id`
- `bundle_payload`
- `created_at`
- `updated_at`

## 3. 配置与资源

当前已依赖：

- 表情识别模型配置
- 姿态识别模型配置
- 文本情感识别模型配置
- 语音情感识别模型配置
- 采样率、窗口长度和时间同步配置

当前明确不纳入：

- ASR 语音转写模型配置
- EEG 通道映射与脑电推理配置

## 4. 权限与调用

- 浏览器不直接调用本服务
- 由 `gateway-service` 经 `consultation-service` 或 `assessment-service` 协调调用
- 会话必须与问诊会话或量表会话建立明确绑定关系

## 5. 输出约束

- 特征输出必须带时间范围和质量标记
- 缺失某种模态时，允许输出部分特征包
- 单模态结果不能被标记为“最终风险结论”
- 当前阶段的 `audio-turns` 只处理语音情感和可选文本情感，不负责 ASR
