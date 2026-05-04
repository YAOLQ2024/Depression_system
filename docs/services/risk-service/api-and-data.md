# `risk-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/risk/evaluations` | `POST` | 创建一次风险评估 | 规划中 |
| `/api/v1/risk/evaluations/{evaluation_id}` | `GET` | 获取风险评估结果 | 规划中 |
| `/api/v1/risk/evaluations/{evaluation_id}/explanations` | `GET` | 获取风险解释详情 | 规划中 |
| `/api/v1/risk/evaluations/{evaluation_id}/override` | `POST` | 人工复核/覆盖标记 | 规划中 |

## 2. 核心实体

### 2.1 risk_evaluation

- `evaluation_id`
- `user_id`
- `consultation_session_id`
- `assessment_session_id`
- `multimodal_bundle_id`
- `rule_set_id`
- `risk_level`
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

## 3. 配置与资源

必须读取：

- `packages/workflow-resources/risk-rules/consultation-v1.yaml`

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
