# `multimodal-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/multimodal/sessions` | `POST` | 创建多模态采集会话 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}` | `GET` | 获取会话状态 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/transcriptions` | `POST` | 提交语音并返回转写结果 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/captures/face` | `POST` | 提交表情采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/captures/pose` | `POST` | 提交姿态采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/captures/eeg` | `POST` | 提交脑电采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/bundle` | `GET` | 获取标准化特征包 | 规划中 |

## 2. 核心实体

### 2.1 multimodal_session

- `session_id`
- `owner_service`
- `owner_session_id`
- `user_id`
- `stage_context`
- `status`
- `started_at`
- `updated_at`

### 2.2 multimodal_capture

- `capture_id`
- `session_id`
- `modality`
- `segment_index`
- `source_uri`
- `capture_started_at`
- `capture_ended_at`
- `processing_status`

### 2.3 multimodal_feature_bundle

- `bundle_id`
- `session_id`
- `speech_transcript`
- `speech_features`
- `face_features`
- `pose_features`
- `eeg_features`
- `quality_flags`
- `generated_at`

## 3. 配置与资源

后续可能依赖：

- 语音转写模型配置
- 表情识别模型配置
- 姿态识别模型配置
- 脑电通道映射配置
- 采样率、窗口长度和时间同步配置

## 4. 权限与调用

- 浏览器不直接调用本服务
- 由 `gateway-service` 经 `consultation-service` 或 `assessment-service` 协调调用
- 会话必须与问诊会话或量表会话建立明确绑定关系

## 5. 输出约束

- 特征输出必须带时间范围和质量标记
- 缺失某种模态时，允许输出部分特征包
- 单模态结果不能被标记为“最终风险结论”
