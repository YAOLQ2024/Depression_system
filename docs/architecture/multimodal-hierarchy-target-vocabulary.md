# 多模态层级重构目标命名冻结

## 1. 文档目的

这份文档用于完成执行计划中的 `Step 1：冻结目标口径`。

从本文件开始，后续数据库迁移、Pydantic schema、SQLAlchemy model、service 方法、API 路径、前端状态字段，统一使用这里定义的目标命名。

如果旧代码里还有旧术语，可以保留兼容一段时间，但**不得再引入新的旧命名**。

核心设计依据来自 [multimodal-five-layer-hierarchy-qa.md](/e:/DataSets/Projects/depression-system/docs/architecture/multimodal-five-layer-hierarchy-qa.md)。

## 2. 冻结的 8 个核心实体名

这 8 个实体名从现在开始冻结：

| 层级 | 冻结实体名 | 用途 |
| --- | --- | --- |
| L1 | `encounter_session` | 一次完整就诊 |
| L2 | `consultation_flow_run` | 数字人问诊流程运行实例 |
| L2 | `assessment_flow_run` | 量表问诊流程运行实例 |
| L4 | `turn` | 一次完整问答窗口 |
| L2.5 | `multimodal_flow_session` | 一个流程下的连续模态容器 |
| L5 | `multimodal_sample` | 连续模态单次采样 |
| L5 | `multimodal_observation` | 对采样的一次推理结果 |
| L4.5 | `multimodal_turn_summary` | 一个 turn 的最终多模态汇总 |

说明：

- `consultation_flow_run` 和 `assessment_flow_run` 虽然都属于 `flow_run`，但在当前项目中继续拆成两个实体更清楚。
- `multimodal_flow_session` 不是顶层 session，也不是 turn，它是“某个流程运行下的连续模态容器”。

## 3. 冻结的 8 个核心作用域字段

这 8 个字段名从现在开始冻结：

| 字段名 | 语义 |
| --- | --- |
| `encounter_session_id` | 顶层完整就诊主键 |
| `flow_run_id` | 当前流程实例主键 |
| `flow_type` | 当前流程类型，取值 `consultation` / `assessment` |
| `turn_id` | 当前问答窗口主键 |
| `stage_id` | 当前流程内部阶段 |
| `question_key` | 当前问题项唯一键 |
| `sample_index` | 连续模态采样序号 |
| `live_state_payload` | 实时看板读取的连续模态最新状态 |

## 4. 冻结的辅助字段命名

这些字段不是每张表都必须有，但一旦表达这些语义，命名必须一致：

| 字段名 | 语义 |
| --- | --- |
| `status` | 当前实体状态 |
| `started_at` | 实体开始时间 |
| `completed_at` | 实体完成时间 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |
| `turn_window_started_at` | 当前问答窗口开始时间 |
| `turn_window_completed_at` | 当前问答窗口结束时间 |
| `sample_started_at` | 单次采样开始时间 |
| `sample_ended_at` | 单次采样结束时间 |
| `captured_at` | 单次采样或结果落定时间 |
| `sample_payload` | 采样原始载荷 |
| `observation_payload` | 推理结果载荷 |
| `turn_summary_payload` | 一个 turn 的最终多模态汇总 |
| `label_distribution` | 一个窗口内的类别分布 |
| `quality_distribution` | 一个窗口内的质量分布 |

## 5. 明确废弃的旧命名

以下命名从现在开始进入废弃态：

| 旧命名 | 替换为 |
| --- | --- |
| `consultation_session_id` | `consultation_flow_run_id` 或 `flow_run_id` |
| `consultation_turn_id` | `turn_id` |
| `prompt_key` | `question_key` |
| `frame_index` | `sample_index` |
| `capture_started_at` | `sample_started_at` |
| `capture_ended_at` | `sample_ended_at` |
| `owner_service` | `flow_type` |
| `owner_session_id` | `flow_run_id` |
| `session_summary_payload` | 删除，不再作为正式目标字段 |

说明：

- `consultation_session_id` 在 consultation 专属上下文里可以短期保留兼容，但目标口径不再使用它作为泛用字段。
- `owner_service` / `owner_session_id` 只是一种历史 owner 绑定表达，不适合作为正式层级字段。

## 6. 当前项目的正式语义口径

后续所有设计、代码评审、字段命名，按下面的定义执行：

### 6.1 `encounter_session`

表示一次完整就诊，覆盖：

- 数字人问诊流程
- 量表问诊流程
- 后续可能扩展的人审、干预或回访流程

### 6.2 `consultation_flow_run`

表示数字人问诊流程的一次运行。

当前 `consultation_sessions` 未来目标就是这一层。

### 6.3 `assessment_flow_run`

表示量表问诊流程的一次运行。

当前 `assessment_sessions` 未来目标就是这一层。

### 6.4 `turn`

表示一次完整问答窗口：

- 数字人问一个问题
- 用户完成一次回答

`turn_id` 必须在回答窗口开始时生成，而不是录音结束后才生成。

### 6.5 `multimodal_sample`

表示连续模态单次采样：

- face：一张采样图
- pose：一张采样图
- eeg：一段采样窗口

### 6.6 `multimodal_observation`

表示对一个 sample 的推理结果。

它不是 UI 状态，不是 turn 汇总，而是“单次采样 -> 单次结果”。

### 6.7 `multimodal_turn_summary`

表示一个 turn 的最终汇总。

对于连续模态，主统计结果采用：

- `sample_count`
- `valid_sample_count`
- `label_distribution`
- `quality_distribution`

不把 `top_3_labels` 作为 turn 级主统计结构。

## 7. API 和代码命名约束

后续代码重构时，统一遵守：

### 7.1 API 路径语义

- `/encounters`
- `/consultation-flows`
- `/assessment-flows`
- `/multimodal-flow-sessions`
- `/turns/{turn_id}/summary`

### 7.2 代码命名语义

- `create_encounter_session`
- `create_consultation_flow_run`
- `create_assessment_flow_run`
- `open_turn_window`
- `close_turn_window`
- `append_multimodal_sample`
- `record_multimodal_observation`
- `finalize_turn_summary`

### 7.3 禁止新增的旧风格命名

从现在开始，禁止新增：

- `consultation_turn_id`
- `prompt_key`
- `frame_index`
- `owner_session_id`
- `session_summary_payload`

## 8. Step 1 完成标准

当满足下面条件时，`Step 1` 视为完成：

1. 后续所有设计稿和代码改动都以本文件命名为准。
2. 新增 schema、model、service 不再引入旧命名。
3. 下一步 `Step 2` 可以基于本文件做旧表旧字段映射。
