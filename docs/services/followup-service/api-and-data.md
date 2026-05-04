# `followup-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/followups/reviews` | `POST` | 创建回顾记录 | 规划中 |
| `/api/v1/followups/reviews/{review_id}` | `GET` | 获取回顾详情 | 规划中 |
| `/api/v1/followups/timelines/{user_id}` | `GET` | 获取用户时间线 | 规划中 |
| `/api/v1/followups/reassessments` | `POST` | 创建再评估任务 | 规划中 |
| `/api/v1/followups/reassessments/{task_id}` | `PATCH` | 更新再评估任务状态 | 规划中 |
| `/api/v1/followups/reports/export` | `POST` | 生成导出报告 | 规划中 |

## 2. 核心实体

### 2.1 conversation_review_record

- `review_id`
- `user_id`
- `consultation_session_id`
- `assessment_session_id`
- `risk_evaluation_id`
- `intervention_session_id`
- `summary_text`
- `created_at`

### 2.2 timeline_event

- `event_id`
- `user_id`
- `event_type`
- `event_source`
- `source_id`
- `event_time`
- `event_summary`

### 2.3 reassessment_task

- `task_id`
- `user_id`
- `trigger_source`
- `scheduled_at`
- `status`
- `reason`
- `next_round_entry`

### 2.4 exportable_report

- `report_id`
- `user_id`
- `range_start`
- `range_end`
- `status`
- `download_uri`

## 3. 输入来源

来自上游的核心输入：

- 问诊记录包
- 量表提交记录
- 多模态特征摘要
- 风险结果
- 干预执行记录
- 用户反馈

## 4. 权限与调用

- 患者侧可查看自己的回顾与再评估结果
- 后台角色可检索和导出记录
- 再评估任务更新需要区分患者确认和后台管理两种来源

## 5. 输出约束

- 时间线事件必须可追溯到来源服务和来源记录
- 再评估任务必须能生成下一轮筛查入口信息
- 导出报告应有明确生成状态，不假设同步即时完成
