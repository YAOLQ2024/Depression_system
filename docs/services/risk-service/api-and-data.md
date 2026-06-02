# `risk-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/risk/evaluations` | `POST` | 创建一次风险评估 | 已实现 |
| `/api/v1/risk/evaluations/{evaluation_id}` | `GET` | 获取风险评估结果 | 已实现 |
| `/api/v1/risk/evaluations/{evaluation_id}/explanations` | `GET` | 获取风险解释详情 | 已实现 |
| `/api/v1/risk/evaluations/{evaluation_id}/override` | `POST` | 人工复核/覆盖标记 | 已预留，当前返回 `501` |

## 1.1 已实现接口说明

### `POST /api/v1/risk/evaluations`

用途：
创建一次临床决策评估，允许显式传入 payload，也允许只传上游 session id 由 `risk-service` 自行回查。

请求体核心字段：

- `user_id`
- `encounter_session_id`
- `consultation_session_id`
- `assessment_session_id`
- `multimodal_session_id`
- `rule_set_id`
- `consultation_payload`
- `assessment_aggregate_payload`
- `multimodal_feature_bundle`

当前支持的输入回退策略：

- 有 `assessment_session_id` 时，优先读取 `aggregate_payload`，否则回退使用量表阶段当前 `results`
- 有 `consultation_session_id` 时，优先读取问诊完整 session
- 量表回查失败但已携带 `source_handoff` 时，可先使用移交 payload
- 有 `multimodal_session_id` 但最终特征包接口未就绪时，先回退读取 `multimodal live snapshot`

### `GET /api/v1/risk/evaluations/{evaluation_id}`

返回：

- 评估主记录
- 上游输入快照
- 触发器明细
- 标准化结果 payload

### `GET /api/v1/risk/evaluations/{evaluation_id}/explanations`

返回：

- `risk_level`
- `safety_risk_level`
- `depression_score`
- `depression_severity`
- `requires_human_review`
- `triggers`
- `risk_explanation`
- `referral_recommendations`
- `lifestyle_suggestions`
- `front_display`

### `POST /api/v1/risk/evaluations/{evaluation_id}/override`

当前仅预留接口，不落库、不改写结果，统一返回 `501`。
后续接人工复核工作流时，沿用以下预留字段：

- `override_risk_level`
- `review_decision`
- `review_note`
- `reviewer_id`
- `metadata`

## 2. 核心实体

### 2.1 risk_evaluation

- `evaluation_id`
- `user_id`
- `consultation_session_id`
- `assessment_session_id`
- `multimodal_session_id`
- `encounter_session_id`
- `workflow_id`
- `rule_set_id`
- `risk_level`
- `depression_score`
- `depression_severity`
- `safety_risk_level`
- `requires_human_review`
- `status`
- `created_at`

### 2.2 risk_trigger

- `trigger_id`
- `evaluation_id`
- `trigger_key`
- `trigger_source`
- `trigger_effect`
- `evidence_summary`

### 2.3 risk_result

- `risk_level`
- `risk_explanation`
- `referral_recommendations`
- `lifestyle_suggestions`
- `intervention_entry_payload`
- `front_display`

## 3. 配置与资源

必须读取：

- `packages/workflow-resources/risk-rules/consultation-v1.yaml`
- `packages/workflow-resources/intervention-programs/catalog.yaml`

后续可能补充：

- 风险解释模板
- 转诊建议模板
- 人工复核规则

## 4. 权限与调用

- 浏览器不直接调用本服务
- 由 `gateway-service` 转发、`assessment-service` 或上游流程编排触发
- 人工复核接口仅后台角色可用

## 5. 输出约束

- 输出必须同时适合前端展示和下游服务消费
- 若触发 `high` 或 `urgent`，必须标记 `requires_human_review = true`
- 输出中应明确区分“硬触发结果”和“聚合判断结果”
- 输出中应返回 `missing_inputs` 与 `pending_integrations`，方便主链联调时识别占位依赖
