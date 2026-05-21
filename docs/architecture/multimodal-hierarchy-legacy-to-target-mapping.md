# 多模态层级重构旧表旧字段映射

## 1. 文档目的

这份文档用于完成执行计划中的 `Step 2：做旧表到新口径的映射清单`。

目标是把当前仓库里的：

- 旧表
- 旧字段
- 旧命名
- 旧作用域表达

逐项映射到目标层级架构。

冻结命名以 [multimodal-hierarchy-target-vocabulary.md](/e:/DataSets/Projects/depression-system/docs/architecture/multimodal-hierarchy-target-vocabulary.md) 为准。

## 2. 当前表到目标实体映射

| 当前表 | 目标实体 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `consultation_sessions` | `consultation_flow_run` | 保留表，后续重命名 | 当前语义最接近数字人问诊流程实例 |
| `assessment_sessions` | `assessment_flow_run` | 保留表，后续重命名 | 当前语义最接近量表问诊流程实例 |
| 无 | `encounter_session` | 新增表 | 当前项目缺失的顶层就诊实体 |
| `consultation_turns` | `turn` | 保留表 | 当前已是 turn 层主表 |
| `multimodal_sessions` | `multimodal_flow_session` | 保留表，后续重命名 | 当前是连续模态容器，但 owner 语义不正式 |
| `multimodal_captures` | `multimodal_sample` | 保留表，后续重命名 | 当前最接近 sample 层 |
| `multimodal_inference_results` | `multimodal_observation` | 保留表，后续重命名 | 当前最接近 observation 层 |
| `multimodal_turn_bundles` | `multimodal_turn_summary` | 保留表，后续重命名 | 当前最接近 turn 汇总层 |
| `multimodal_audio_turns` | `turn_audio_asset` | 保留表，后续重命名 | 当前承载一轮回答的音频任务与资产状态 |

## 3. 当前主链关系到目标主链关系

## 3.1 当前主链

当前主链大致是：

- `consultation_sessions.id`
- `assessment_sessions.consultation_session_id`
- `multimodal_sessions.owner_service + owner_session_id`
- `consultation_turns.session_id`
- `multimodal_captures.consultation_turn_id`
- `multimodal_inference_results.consultation_turn_id`

这条链的问题是：

1. 顶层没有完整就诊主键。
2. `consultation_session` 被同时拿来表达“流程实例”和“顶层 session”。
3. multimodal 通过 owner 语义挂接，不够稳定。

## 3.2 目标主链

目标主链应改为：

- `encounter_sessions.id`
- `consultation_flow_runs.encounter_session_id`
- `assessment_flow_runs.encounter_session_id`
- `consultation_turns.consultation_flow_run_id`
- `multimodal_flow_sessions.flow_run_id`
- `multimodal_samples.turn_id`
- `multimodal_observations.turn_id`
- `multimodal_turn_summaries.turn_id`

## 4. consultation 侧字段映射

## 4.1 `consultation_sessions`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `consultation_flow_run_id` | 保留值，改语义 | 未来表重命名后仍用同一主键 |
| `user_id` | `user_id` | 保留 | 无需变化 |
| `workflow_id` | `workflow_id` | 保留 | 无需变化 |
| `workflow_stage_id` | 删除 | 后续删除 | 由 `flow_type + current_stage_id` 替代 |
| `current_stage_id` | `current_stage_id` | 保留 | 继续表示流程内部阶段 |
| `current_node_id` | `current_node_id` | 保留 | 继续表示节点态 |
| `current_prompt_key` | `current_question_key` | 重命名 | `prompt` 统一退场 |
| `current_prompt_order` | `current_question_order` | 重命名 | 语义更清楚 |
| `current_prompt_video_asset_id` | `current_question_video_asset_id` | 重命名 | 统一 question 语义 |
| `current_prompt_video_uri` | `current_question_video_uri` | 重命名 | 统一 question 语义 |
| `current_prompt_question_text` | `current_question_text` | 重命名 | 统一 question 语义 |
| `current_prompt_subtitle_text` | `current_question_subtitle_text` | 重命名 | 统一 question 语义 |
| `total_prompt_count` | `total_question_count` | 重命名 | 统一 question 语义 |
| `completed_prompt_count` | `completed_question_count` | 重命名 | 统一 question 语义 |
| `status` | `status` | 保留 | 无需变化 |
| `multimodal_session_id` | `multimodal_flow_session_id` | 重命名 | 连续模态容器语义更准确 |
| `multimodal_live_payload` | `multimodal_live_state_payload` | 重命名 | 与目标词汇对齐 |
| `multimodal_live_updated_at` | `multimodal_live_updated_at` | 保留 | 无需变化 |
| 无 | `encounter_session_id` | 新增 | 挂到完整就诊主链 |

## 4.2 `consultation_turns`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `turn_id` | 保留值，改语义 | 继续作为 turn 主键 |
| `session_id` | `consultation_flow_run_id` | 重命名 | 明确挂到 flow run |
| `workflow_stage_id` | 删除 | 后续删除 | 由上层 flow 和 stage 表达 |
| `stage_id` | `stage_id` | 保留 | 无需变化 |
| `node_id` | `node_id` | 保留 | 无需变化 |
| `turn_index` | `turn_index` | 保留 | 无需变化 |
| `prompt_key` | `question_key` | 重命名 | 统一 question 语义 |
| `prompt_order` | `question_order` | 重命名 | 统一 question 语义 |
| `prompt_video_asset_id` | `question_video_asset_id` | 重命名 | 统一 question 语义 |
| `prompt_video_uri` | `question_video_uri` | 重命名 | 统一 question 语义 |
| `prompt_question_text` | `question_text` | 重命名 | 统一 question 语义 |
| `prompt_subtitle_text` | `question_subtitle_text` | 重命名 | 统一 question 语义 |
| `response_started_at` | `turn_window_started_at` | 重命名 | 与回答窗口语义对齐 |
| `response_completed_at` | `turn_window_completed_at` | 重命名 | 与回答窗口语义对齐 |
| `multimodal_bundle_payload` | `turn_summary_payload` | 重命名 | 与目标实体语义对齐 |
| 无 | `encounter_session_id` | 新增 | 便于跨流程追踪和查询 |

## 5. assessment 侧字段映射

## 5.1 `assessment_sessions`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `assessment_flow_run_id` | 保留值，改语义 | 未来表重命名后沿用 |
| `consultation_session_id` | `source_consultation_flow_run_id` | 重命名 | 表示来源流程，而不是顶层 session |
| `user_id` | `user_id` | 保留 | 无需变化 |
| `status` | `status` | 保留 | 无需变化 |
| `required_scales` | `required_scales` | 保留 | 无需变化 |
| `selected_scales` | `selected_scales` | 保留 | 无需变化 |
| `current_scale_slug` | `current_scale_slug` | 保留 | 无需变化 |
| `current_item_index` | `current_item_index` | 保留 | 无需变化 |
| `capture_context` | `capture_context` | 保留 | 当前先不改命名 |
| 无 | `encounter_session_id` | 新增 | 挂到完整就诊主链 |
| 无 | `workflow_id` | 新增 | 与 consultation 侧对齐 |
| 无 | `current_stage_id` | 新增 | 为未来量表阶段化预留 |

## 6. multimodal 侧字段映射

## 6.1 `multimodal_sessions`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `multimodal_flow_session_id` | 保留值，改语义 | 未来表重命名后沿用 |
| `owner_service` | `flow_type` | 替换 | owner 语义退场 |
| `owner_session_id` | `flow_run_id` | 替换 | owner 语义退场 |
| `user_id` | `user_id` | 保留 | 无需变化 |
| `stage_context.stage_id` | `current_stage_id` | 抽出成显式字段 | 不再只藏在 JSON 里 |
| `stage_context.stage_label` | `current_stage_label` | 抽出成显式字段 | 不再只藏在 JSON 里 |
| `stage_context.stage_order` | `current_stage_order` | 抽出成显式字段 | 不再只藏在 JSON 里 |
| `latest_live_payload` | `live_state_payload` | 重命名 | 目标实时看板载荷 |
| `session_summary_payload` | 删除 | 后续删除 | 正式目标不再保留 session summary |
| 无 | `encounter_session_id` | 新增 | 挂到完整就诊主链 |

## 6.2 `multimodal_captures`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `sample_id` | 保留值，改语义 | 单次采样主键 |
| `session_id` | `multimodal_flow_session_id` | 重命名 | 明确挂到 multimodal 容器 |
| `consultation_turn_id` | `turn_id` | 重命名 | 不再 consultation 限定 |
| `modality` | `modality` | 保留 | 无需变化 |
| `capture_kind` | `sample_kind` | 重命名 | 与目标词汇对齐 |
| `source_ref_id` | `source_ref_id` | 保留 | 无需变化 |
| `storage_uri` | `storage_uri` | 保留 | 无需变化 |
| `capture_payload` | `sample_payload` | 重命名 | 与目标词汇对齐 |
| `captured_at` | `captured_at` | 保留 | 无需变化 |
| `capture_payload.consultation_session_id` | `flow_run_id` | 提升成显式字段 | 不再只放 JSON |
| `capture_payload.question_key` | `question_key` | 提升成显式字段 | 不再只放 JSON |
| `capture_payload.frame_index` | `sample_index` | 提升成显式字段 | 不再叫 frame index |
| `capture_payload.capture_started_at` | `sample_started_at` | 提升成显式字段 | 不再叫 capture started |
| `capture_payload.capture_ended_at` | `sample_ended_at` | 提升成显式字段 | 不再叫 capture ended |
| 无 | `stage_id` | 新增 | 显式阶段作用域 |
| 无 | `encounter_session_id` | 新增 | 便于跨流程查询 |
| 无 | `flow_type` | 新增 | consultation / assessment |

## 6.3 `multimodal_inference_results`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `observation_id` | 保留值，改语义 | 单次推理结果主键 |
| `session_id` | `multimodal_flow_session_id` | 重命名 | 明确挂到 multimodal 容器 |
| `consultation_turn_id` | `turn_id` | 重命名 | 不再 consultation 限定 |
| `modality` | `modality` | 保留 | 无需变化 |
| `source_kind` | `source_kind` | 保留 | 无需变化 |
| `source_ref_id` | `source_ref_id` | 保留 | 无需变化 |
| `inference_payload` | `observation_payload` | 重命名 | 与目标词汇对齐 |
| `captured_at` | `captured_at` | 保留 | 无需变化 |
| 无 | `sample_id` | 新增 | 显式关联 sample |
| 无 | `flow_run_id` | 新增 | 显式流程作用域 |
| 无 | `stage_id` | 新增 | 显式阶段作用域 |
| 无 | `question_key` | 新增 | 显式问题作用域 |
| 无 | `encounter_session_id` | 新增 | 便于跨流程查询 |
| 无 | `flow_type` | 新增 | consultation / assessment |

## 6.4 `multimodal_turn_bundles`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `id` | 保留 | 无需变化 |
| `session_id` | `multimodal_flow_session_id` | 重命名 | 明确挂到 multimodal 容器 |
| `consultation_turn_id` | `turn_id` | 重命名 | 不再 consultation 限定 |
| `bundle_payload` | `summary_payload` | 重命名 | 与目标词汇对齐 |
| `created_at` | `generated_at` | 重命名语义 | 强调这是生成时间 |
| `updated_at` | `updated_at` | 保留 | 无需变化 |
| 无 | `flow_run_id` | 新增 | 显式流程作用域 |
| 无 | `stage_id` | 新增 | 显式阶段作用域 |
| 无 | `question_key` | 新增 | 显式问题作用域 |
| 无 | `encounter_session_id` | 新增 | 便于跨流程查询 |
| 无 | `flow_type` | 新增 | consultation / assessment |

## 6.5 `multimodal_audio_turns`

| 当前字段 | 目标字段 | 处理方式 | 说明 |
| --- | --- | --- | --- |
| `id` | `turn_audio_asset_id` | 改语义 | 更准确表达用途 |
| `multimodal_session_id` | `multimodal_flow_session_id` | 重命名 | 与新命名对齐 |
| `consultation_session_id` | `consultation_flow_run_id` | 重命名 | 不再使用 consultation session 泛名 |
| `turn_id` | `turn_id` | 保留 | 无需变化 |
| `stage_id` | `stage_id` | 保留 | 无需变化 |
| `question_key` | `question_key` | 保留 | 无需变化 |
| `prompt_key` | 删除 | 后续删除 | question 语义统一 |
| `response_started_at` | `turn_window_started_at` | 重命名 | 与 turn 对齐 |
| `response_completed_at` | `turn_window_completed_at` | 重命名 | 与 turn 对齐 |
| 无 | `encounter_session_id` | 新增 | 便于跨流程查询 |
| 无 | `flow_run_id` | 新增 | 泛化流程作用域 |

## 7. 旧字段去留清单

## 7.1 继续保留的字段

- `user_id`
- `workflow_id`
- `status`
- `stage_id`
- `turn_id`
- `question_key`
- `created_at`
- `updated_at`
- `started_at`
- `completed_at`

## 7.2 需要重命名的字段

- `consultation_session_id -> consultation_flow_run_id`
- `consultation_turn_id -> turn_id`
- `prompt_key -> question_key`
- `frame_index -> sample_index`
- `capture_started_at -> sample_started_at`
- `capture_ended_at -> sample_ended_at`
- `latest_live_payload -> live_state_payload`
- `multimodal_bundle_payload -> turn_summary_payload`

## 7.3 需要删除的字段

- `workflow_stage_id`
- `owner_service`
- `owner_session_id`
- `session_summary_payload`

## 8. 代码层的直接影响模块

下面这些模块会受到这次映射调整的直接影响：

### 8.1 consultation-service

- `app/models/consultation_session.py`
- `app/models/consultation_turn.py`
- `app/schemas/consultations.py`
- `app/services/consultation_engine.py`
- `app/clients/multimodal_client.py`

### 8.2 assessment-service

- `app/models/assessment_session.py`
- `app/schemas/assessment.py`
- `app/services/assessment_engine.py`

### 8.3 multimodal-service

- `app/models/multimodal_session.py`
- `app/models/multimodal_capture.py`
- `app/models/multimodal_inference_result.py`
- `app/models/multimodal_turn_bundle.py`
- `app/models/multimodal_audio_turn.py`
- `app/schemas/multimodal.py`
- `app/services/multimodal_session_service.py`
- `app/services/multimodal_store.py`
- `app/api/multimodal.py`

## 9. Step 2 完成标准

当满足下面条件时，`Step 2` 视为完成：

1. 每张旧表都有明确的目标实体。
2. 每个旧字段都知道未来是保留、重命名还是删除。
3. 已经能据此进入 `Step 3：数据库加法迁移`。
