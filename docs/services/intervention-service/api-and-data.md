# `intervention-service` 服务接口与数据

## 0. 当前已落地最小闭环

- 已实现创建干预执行会话
- 已实现查询干预执行会话
- 已实现写入干预执行事件
- 已实现查询干预执行事件列表

当前患者端绑定规则：

- 如果是问诊/量表完成后从结果页进入调节干预，则写入 `consultation_session_id`
- 如果是首页直接进入调节干预，则 `consultation_session_id` 留空

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/interventions/plans` | `POST` | 生成干预计划 | 规划中 |
| `/api/v1/interventions/sessions` | `POST` | 创建干预执行会话 | 规划中 |
| `/api/v1/interventions/sessions/{session_id}` | `GET` | 获取执行状态 | 规划中 |
| `/api/v1/interventions/sessions/{session_id}/events` | `POST` | 写入执行事件 | 规划中 |
| `/api/v1/interventions/sessions/{session_id}/feedback` | `POST` | 提交用户反馈 | 规划中 |
| `/api/v1/interventions/sessions/{session_id}/complete` | `POST` | 完成干预执行 | 规划中 |

## 2. 核心实体

### 2.1 intervention_plan

- `plan_id`
- `user_id`
- `risk_evaluation_id`
- `program_ids`
- `delivery_modes`
- `intensity_level`
- `duration_minutes`
- `guidance_text`

### 2.2 intervention_session

- `session_id`
- `plan_id`
- `status`
- `started_at`
- `updated_at`
- `completed_at`

### 2.3 intervention_feedback

- `feedback_id`
- `session_id`
- `user_rating`
- `completion_status`
- `self_report_text`
- `followup_hint`
- `created_at`

## 3. 配置与资源

必须读取：

- `packages/workflow-resources/intervention-programs/catalog.yaml`

后续可能补充：

- 具体干预方案详情文件
- 音视频/图文资源映射表
- 时长和禁忌条件配置

## 4. 权限与调用

- 患者侧通过 `gateway-service` 调用执行接口
- 后台通过 `gateway-service` 查看计划和记录
- 计划生成应绑定既有 `risk_evaluation_id`

## 5. 输出约束

- 干预计划必须包含方式、强度和执行建议
- 执行记录必须保留时间线事件
- 用户反馈必须结构化，便于后续再评估使用
