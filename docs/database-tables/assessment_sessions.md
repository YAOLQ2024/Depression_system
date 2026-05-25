# `assessment_sessions` 表说明

## 1. 表作用

`assessment_sessions` 是量表评估阶段的主会话表，用来保存一次量表流程的整体进度、来源问诊移交信息、当前做到哪份量表哪一题，以及全部量表完成后的聚合结果。

它相当于量表域里的“总控表”。

## 2. 在系统哪一步使用

1. 量表会话启动：`assessment-service` 接收问诊移交数据后创建本表记录。
2. 量表选择与排序：根据 `required_scales`、`selected_scales` 确定本次实际执行的量表序列。
3. 逐题作答：根据 `current_scale_slug` 和 `current_item_index` 返回当前题目。
4. 单量表完成：写入 `assessment_results` 后，更新本表指向下一份量表。
5. 全量表完成：状态改为 `completed`，并生成 `aggregate_payload` 供后续风险服务消费。

## 3. 字段说明

| 字段名 | 英文翻译 | 中文翻译 | 类型/约束 | 作用 | 为什么需要这个字段 | 主要使用步骤 |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | Assessment Session ID | 量表会话ID | `String(36)`，主键 | 唯一标识一次完整量表评估。 | 用户可能有多次量表评估，需要独立会话主键来区分和追踪。 | 会话创建、作答、结果聚合 |
| `user_id` | User ID | 用户ID | `String(255)`，索引，非空 | 标识该量表会话属于哪位用户。 | 服务需要防止跨用户读取或写入量表答案。 | 会话创建、权限校验 |
| `consultation_session_id` | Consultation Session ID | 来源问诊会话ID | `String(36)`，索引，可空 | 关联这次量表评估源自哪场问诊。 | 量表不是凭空开始的，需要和上游问诊链路建立可追溯关联。 | 会话创建、结果回溯 |
| `status` | Session Status | 会话状态 | `String(64)`，非空 | 标识当前量表会话状态，如 `in_progress` 或 `completed`。 | 前端和下游服务需要明确知道量表是否仍在进行中。 | 全流程 |
| `required_scales` | Required Scales | 必做量表列表 | `JSON`，非空 | 保存来自问诊移交层面要求必须完成的量表。 | 需要保留“业务上要求做哪些量表”的原始约束，而不是只保存最终执行结果。 | 会话创建、流程约束 |
| `selected_scales` | Selected Scales | 实际执行量表列表 | `JSON`，非空 | 保存当前会话经过校验与去重后的量表顺序。 | 实际执行序列可能与原始要求不完全相同，需要单独保存最终决策。 | 会话创建、量表切换 |
| `current_scale_slug` | Current Scale Slug | 当前量表标识 | `String(128)`，可空 | 指向当前正在进行的量表。 | 服务返回下一题时必须知道当前处于哪一份量表。 | 逐题作答、单量表切换 |
| `current_item_index` | Current Item Index | 当前题目序号 | `Integer`，非空 | 记录当前量表进行到第几题。 | 没有题号就无法定位当前题，也无法防止乱序提交。 | 逐题作答 |
| `scale_handoff_payload` | Scale Handoff Payload | 问诊移交载荷 | `JSON`，可空 | 保存从问诊服务带来的摘要、症状筛查、高风险结果和必做量表列表。 | 量表服务需要保留上游背景，后续聚合和风控也需要知道量表是基于什么上下文启动的。 | 会话创建、结果聚合 |
| `capture_context` | Capture Context | 采集上下文 | `JSON`，可空 | 保存语音、视频或设备采集相关的上下文。 | 多模态分析需要知道作答时的采集环境，不能只看答案文本。 | 会话创建、后续多模态关联 |
| `aggregate_payload` | Aggregate Payload | 聚合结果载荷 | `JSON`，可空 | 保存全量表完成后的组合结果。 | 风险服务和其他下游系统更适合直接消费聚合结果，而不是自行汇总多张表。 | 全量表完成、服务移交 |
| `notes` | Notes | 备注 | `Text`，可空 | 预留给人工备注或特殊处理信息。 | 真实业务里经常需要记录例外情况，提前预留字段比后续紧急改表更稳。 | 预留字段，当前版本未主动写入 |
| `created_at` | Created Time | 创建时间 | `DateTime(timezone=True)`，非空 | 记录量表会话创建时间。 | 需要审计、排序以及和问诊完成时间进行对比。 | 会话创建 |
| `updated_at` | Updated Time | 更新时间 | `DateTime(timezone=True)`，非空 | 记录最近一次进度变化时间。 | 前端刷新状态、排障和任务监控都依赖更新时间。 | 逐题作答、量表切换 |
| `started_at` | Started Time | 开始时间 | `DateTime(timezone=True)`，可空 | 记录量表正式开始时间。 | 区分“会话被创建”与“用户开始作答”是必要的统计信息。 | 会话创建、时长统计 |
| `completed_at` | Completed Time | 完成时间 | `DateTime(timezone=True)`，可空 | 记录所有量表完成的时间。 | 需要计算量表总耗时，并作为下游消费的完成时间标记。 | 全量表完成 |

## 4. 备注

- `required_scales` 强调“业务必须做什么”，`selected_scales` 强调“当前这次实际按什么顺序做”。
- `aggregate_payload` 的存在说明系统设计上希望下游服务直接消费汇总结果，而不是自己重查答案和得分。
