# `consultation-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/consultations` | `POST` | 创建问诊会话 | 已实现 |
| `/api/v1/consultations/{session_id}` | `GET` | 获取当前问诊状态 | 已实现 |
| `/api/v1/consultations/{session_id}/start` | `POST` | 从问诊准备进入正式问诊 | 已实现 |
| `/api/v1/consultations/{session_id}/question-items/{question_key}/complete` | `POST` | 标记一个无需用户回答的系统视频项已播放完成，并推进到下一阶段/下一题 | 已实现 |
| `/api/v1/consultations/{session_id}/turns` | `POST` | 提交一轮患者输入 | 已实现 |
| `/api/v1/consultations/{session_id}/manual-input` | `POST` | 提交文字兜底输入 | 规划中 |
| `/api/v1/consultations/{session_id}/complete` | `POST` | 完成问诊并生成量表移交数据 | 规划中 |

## 2. 核心实体

### 2.1 consultation_session

- `session_id`
- `user_id`
- `workflow_id`
- `script_bundle`
- `playlist_version`
- `playlist_manifest_status`
- `delivery_mode`
- `current_stage_id`
- `current_node_id`
- `current_stage`
- `current_question_item`
- `status`
- `current_prompt_key`
- `current_prompt_order`
- `current_prompt_video_asset_id`
- `current_prompt_video_uri`
- `current_prompt_question_text`
- `current_prompt_subtitle_text`
- `total_prompt_count`
- `completed_prompt_count`
- `assigned_doctor_persona`
- `started_at`
- `updated_at`
- `completed_at`

其中：

- `current_stage`
  - 当前真实问诊阶段摘要
  - 至少包含：
    - `stage_id`
    - `stage_label`
    - `stage_order`
    - `total_stages`
- `current_question_item`
  - 当前固定视频问题项摘要
  - 至少包含：
    - `question_key`
    - `node_id`
    - `video_asset_id`
    - `video_uri`
    - `question_text`
    - `subtitle_text`
    - `response_required`

### 2.2 consultation_turn

- `turn_id`
- `session_id`
- `stage_id`
- `node_id`
- `turn_index`
- `prompt_key`
- `prompt_order`
- `prompt_video_asset_id`
- `prompt_video_uri`
- `prompt_question_text`
- `prompt_subtitle_text`
- `input_type`
- `raw_input`
- `transcript_text`
- `structured_fields`
- `branch_taken`
- `response_started_at`
- `response_completed_at`
- `created_at`

补充说明：

- 当 `status = waiting_system_completion` 时，表示当前问题项是 `response_required = false` 的系统视频项
- 此时前端应在视频播放结束后调用 `/question-items/{question_key}/complete`
- 问候说明阶段不再要求用户手动说“开始”或点击继续

### 2.3 consultation_summary

- `chief_complaint_raw_text`
- `chief_complaint_summary`
- `current_history_structured_result`
- `high_risk_screening_result`
- `scale_handoff_payload`

## 3. 配置资源

必须读取：

- `workflows/consultation-v1.yaml`
- `digital-human-playlists/consultation-v1.yaml`
- `interview-scripts/rule-v1/stage-01-greeting-and-briefing.yaml`
- `interview-scripts/rule-v1/stage-02-chief-complaint.yaml`
- `interview-scripts/rule-v1/stage-03-current-history-followup.yaml`
- `interview-scripts/rule-v1/stage-04-high-risk-screening.yaml`
- `interview-scripts/rule-v1/handoff-to-scale-assessment.yaml`
- `doctor-personas/*.yaml`

## 4. 权限与调用

- 浏览器不直接访问 `consultation-service`
- 由 `gateway-service` 代表已登录用户转发调用
- 服务内部仍需校验用户身份与会话归属

## 5. 高风险输出约束

如果高风险筛查达到 `high` 或 `urgent`：

- 标记 `requires_human_review = true`
- 暂停标准问诊主链
- 生成人工介入所需摘要
- 不直接继续量表阶段
