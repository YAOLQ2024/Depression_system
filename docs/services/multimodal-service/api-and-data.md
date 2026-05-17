# `multimodal-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/multimodal/sessions` | `POST` | 创建多模态采集会话 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}` | `GET` | 获取会话状态 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/audio-turns` | `POST` | 提交一轮原始语音，落 MinIO，并返回 ASR 结果 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/captures/face` | `POST` | 提交表情采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/captures/pose` | `POST` | 提交姿态采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/captures/eeg` | `POST` | 提交脑电采集片段 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/live` | `GET` | 获取前端实时看板聚合状态 | 规划中 |
| `/api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle` | `GET` | 获取某一回答窗口的标准化特征包 | 规划中 |

### 1.1 V1 接口责任分配总表

| 接口 | 方法 | 调用方 | 负责人 | 用途 | 返回核心字段 | 当前状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/v1/multimodal/sessions` | `POST` | `consultation-service` / `assessment-service` | 刘倩 | 创建多模态会话，绑定业务会话和用户上下文 | `session_id` `owner_session_id` `status` `started_at` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}` | `GET` | `consultation-service` / `assessment-service` | 刘倩 | 查询多模态会话状态 | `session_id` `status` `updated_at` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}/audio-turns` | `POST` | `gateway-service`（问诊页录音上传） | 朱睿主责，刘倩配合语音特征 | 一轮原始音频上传、MinIO 落地、Dolphin ASR、语音链路返回 | `audio_turn_id` `audio_uri` `transcript_text` `processing_status` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}/captures/face` | `POST` | `gateway-service`（问诊页摄像头采样上传） | 刘倩 | 提交表情采样帧或片段并落库 | `capture_id` `processing_status` `latest_face_label` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}/captures/pose` | `POST` | `gateway-service`（问诊页姿态采样上传） | 刘倩 | 提交姿态采样帧或片段并落库 | `capture_id` `processing_status` `latest_pose_label` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}/captures/eeg` | `POST` | `gateway-service` 或 `multimodal-service` 内部 EEG provider 适配层 | 金伟 | 提交 EEG 采样片段并生成 EEG 特征 | `capture_id` `processing_status` `latest_eeg_label` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}/live` | `GET` | `gateway-service`（前端右侧实时看板轮询） | 朱睿 + 刘倩 + 金伟 | 返回最近一次可展示的多模态聚合状态 | `speech` `face` `pose` `eeg` `text` `updated_at` | 未实现 |
| `/api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle` | `GET` | `consultation-service` / `risk-service` / `assessment-service` | 朱睿 + 刘倩 + 金伟 | 返回某一回答窗口最终标准化特征包 | `audio_uri` `transcript_text` `speech_features` `face_features` `pose_features` `eeg_features` | 未实现 |

### 1.2 V1 设计原则

- `POST /api/v1/multimodal/sessions` 只是“创建多模态会话”的入口，不负责承载所有模态处理。
- 语音、表情、姿态、EEG 必须拆成独立写接口，避免一个接口承担全部上行职责。
- 前端实时看板不直接拼接多个模态写接口的返回结果，而是统一读取 `/live`。
- 回答窗口结束后，下游服务不直接读 `/live`，而是读取 turn 级 `/bundle`。

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

### 4.1 V1 调用与落库时序

1. 进入正式问诊时，`consultation-service` 调用 `POST /api/v1/multimodal/sessions` 创建多模态会话。
2. 某一道题进入回答窗口后，前端开始本地录音，并在窗口内持续采样 face / pose / EEG。
3. 采样中的实时数据分别提交到：
   - `/captures/face`
   - `/captures/pose`
   - `/captures/eeg`
4. 右侧前端看板只轮询 `/live`，不直接读取各采样写接口响应。
5. 回答结束后，前端把整段语音提交到 `/audio-turns`。
6. `multimodal-service` 对该轮语音完成：
   - MinIO 落地
   - Dolphin ASR
   - 语音链路处理状态写库
7. 主系统根据 `/audio-turns` 返回的 `audio_uri`、`transcript_text`、`processing_status`，把结果绑定回当前 `consultation_turn`。
8. 当该轮语音和其他模态都完成后，`multimodal-service` 生成 turn 级 `bundle`。
9. `consultation-service` 再根据 turn 级结果推进到下一题或下一阶段。

### 4.2 V1 存储层次

- `multimodal_sessions`
  - 会话级上下文
  - 在创建多模态会话时写入
- `multimodal_captures`
  - face / pose / EEG / audio 等采样片段明细
  - 在每次模态数据上行时写入
- `multimodal_feature_bundles`
  - 回答窗口级标准化特征包
  - 在某一道题处理完成后写入
- `consultation_turns`
  - 主问诊 turn 业务表
  - 由主系统回写：
    - `audio_uri`
    - `transcript_text`
    - `response_started_at`
    - `response_completed_at`

## 5. 输出约束

- 特征输出必须带时间范围和质量标记
- 缺失某种模态时，允许输出部分特征包
- 单模态结果不能被标记为“最终风险结论”
- 当前阶段的 `audio-turns` 只处理语音情感和可选文本情感，不负责 ASR
