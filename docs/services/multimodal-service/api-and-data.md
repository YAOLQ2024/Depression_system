# `multimodal-service` 服务接口与数据

## 1. Step 4D 当前对齐范围

当前仓库已按 `docs/apps/consultation/Step4D_其他非EEG接口规范_给刘倩_20260517.md` 对齐以下非 EEG 能力：

- `POST /api/v1/multimodal/sessions/{session_id}/captures/face`
- `POST /api/v1/multimodal/sessions/{session_id}/captures/pose`
- `POST /api/v1/multimodal/sessions/{session_id}/audio-turns`
- `GET /api/v1/multimodal/sessions/{session_id}/live`
- `GET /api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle`

当前明确不包含：

- ASR 语音转写
- MinIO 音频落盘
- EEG 模态
- 最终风险结论

## 2. 对外接口清单

| 接口 | 方法 | 用途 | 当前状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已实现 |
| `/health/ready` | `GET` | 就绪检查 | 已实现 |
| `/api/v1/multimodal/sessions` | `POST` | 创建多模态会话 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}` | `GET` | 获取会话状态 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/warmup` | `POST` | 预热非 EEG 运行时 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/audio-turns` | `POST` | 基于整段音频补齐 `speech_emotion` / `text_emotion` | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/captures/face` | `POST` | 提交 face 连续采样帧并保存细粒度结果 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/captures/pose` | `POST` | 提交 pose 连续采样帧并保存细粒度结果 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/live` | `GET` | 返回前端右侧看板使用的聚合结果 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle` | `GET` | 返回 turn 级标准化特征包 | 已实现 |
| `/api/v1/multimodal/sessions/{session_id}/captures/eeg` | `POST` | 提交脑电采集片段 | 规划中 |

## 3. Step 4D 协议约束

### 3.1 face / pose 连续采样

- `captures/face` 与 `captures/pose` 统一使用 `multipart/form-data`
- 必填字段：
  - `consultation_session_id`
  - `question_key`
  - `capture_started_at`
  - `capture_ended_at`
  - `frame_index`
  - `mime_type`
  - `image_file`
- 可选字段：
  - `turn_id`

### 3.2 实时看板读取

前端只读取：

- `GET /api/v1/multimodal/sessions/{session_id}/live`

返回结构固定包含：

- `speech`
- `text`
- `face`
- `pose`
- `updated_at`

即使某个模态还没有结果，也返回稳定空结构，并设置 `status = pending`。

### 3.3 turn 结束后读取

主链与下游只读取：

- `GET /api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle`

返回结构固定包含：

- `turn_id`
- `session_id`
- `question_key`
- `generated_at`
- `speech_features`
- `text_features`
- `face_features`
- `pose_features`

## 4. 当前落库结构

### 4.1 `multimodal_sessions`

- 会话级上下文
- 最近一次 `/live` 聚合结果
- session 级 `face_summary` / `pose_summary`

### 4.2 `multimodal_captures`

- face / pose / audio 原始采样元数据
- 采样时间范围
- `question_key`
- `frame_index`

### 4.3 `multimodal_inference_results`

- 每次推理后的标准化结果
- `speech` / `text` / `face` / `pose` 细粒度结果
- 用于生成 `/live` 与 turn / session 汇总

### 4.4 `multimodal_turn_bundles`

- 每个 `turn_id` 一条标准化 bundle
- `speech_features`
- `text_features`
- `face_features`
- `pose_features`

## 5. 输出约束

- 字段名固定，不允许 `label` / `emotion` / `dominant_emotion` 混用到对外接口
- `speech` / `text` / `face` / `pose` 都必须带 `status`
- face / pose 写接口返回当前帧结果
- `/live` 返回会话级最新可展示结果
- `/bundle` 返回 turn 级汇总结果
- face / pose 汇总必须带：
  - `summary_type`
  - `primary_label`
  - `primary_score`
  - `top_3_labels`
  - `sample_count`
  - `quality_flags`
