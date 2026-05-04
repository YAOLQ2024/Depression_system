# `consultation-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/consultations` | `POST` | 创建问诊会话 | 规划中 |
| `/api/v1/consultations/{session_id}` | `GET` | 获取当前问诊状态 | 规划中 |
| `/api/v1/consultations/{session_id}/start` | `POST` | 从问诊准备进入正式问诊 | 规划中 |
| `/api/v1/consultations/{session_id}/turns` | `POST` | 提交一轮患者输入 | 规划中 |
| `/api/v1/consultations/{session_id}/manual-input` | `POST` | 提交文字兜底输入 | 规划中 |
| `/api/v1/consultations/{session_id}/complete` | `POST` | 完成问诊并生成量表移交数据 | 规划中 |

## 2. 核心实体

### 2.1 consultation_session

- `session_id`
- `user_id`
- `workflow_id`
- `script_bundle`
- `current_stage_id`
- `current_node_id`
- `status`
- `assigned_doctor_persona`
- `started_at`
- `updated_at`
- `completed_at`

### 2.2 consultation_turn

- `turn_id`
- `session_id`
- `stage_id`
- `node_id`
- `input_type`
- `raw_input`
- `transcript_text`
- `structured_fields`
- `branch_taken`
- `created_at`

### 2.3 consultation_summary

- `chief_complaint_raw_text`
- `chief_complaint_summary`
- `current_history_structured_result`
- `high_risk_screening_result`
- `scale_handoff_payload`

## 3. 配置资源

必须读取：

- `workflows/consultation-v1.yaml`
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
