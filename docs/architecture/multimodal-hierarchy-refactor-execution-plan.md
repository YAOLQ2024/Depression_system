# 多模态层级重构执行计划

## 1. 文档目的

这份文档不讨论概念本身，而是回答一个更直接的问题：

- 第一步先做什么
- 第二步做什么
- 哪一步开始改数据库
- 哪一步开始改代码
- 后续按什么顺序收口旧字段和旧语义

执行口径以 [multimodal-five-layer-hierarchy-qa.md](/e:/DataSets/Projects/depression-system/docs/architecture/multimodal-five-layer-hierarchy-qa.md) 为准。

## 2. 总原则

这次重构按 4 条原则执行：

1. 先定语义，再改表，再改代码，再删旧字段。
2. 先加法兼容，不直接做破坏性重命名。
3. 先打通 `encounter -> flow -> turn -> sample` 主链，再处理缓存和聚合。
4. 连续模态 `face / pose / eeg` 的 turn 绑定必须在回答窗口开始时建立，不能等录音结束。

## 3. 一句话顺序

如果只看一句话，执行顺序就是：

1. 先冻结术语和目标表结构。
2. 再做数据库加法迁移。
3. 再做代码双写和新链路接入。
4. 再切读路径和聚合逻辑。
5. 最后删旧字段、删旧表、删旧命名。

## 4. 分步执行

## Step 1：冻结目标口径

### 目标

把这次重构的目标命名固定下来，避免边改边改名。

### 本步要做什么

确认以下 8 个核心实体名不再变化：

- `encounter_session`
- `consultation_flow_run`
- `assessment_flow_run`
- `turn`
- `multimodal_flow_session`
- `multimodal_sample`
- `multimodal_observation`
- `multimodal_turn_summary`

确认以下 8 个核心字段名不再变化：

- `encounter_session_id`
- `flow_run_id`
- `flow_type`
- `turn_id`
- `stage_id`
- `question_key`
- `sample_index`
- `live_state_payload`

### 本步是否改数据库

不改。

### 本步是否改代码

不改。

### 本步产物

- 本文档
- [multimodal-five-layer-hierarchy-qa.md](/e:/DataSets/Projects/depression-system/docs/architecture/multimodal-five-layer-hierarchy-qa.md)

## Step 2：做旧表到新口径的映射清单

### 目标

先把“现在有什么”和“将来要变成什么”一一对应清楚。

### 本步要做什么

产出一张映射表，至少覆盖：

- `consultation_sessions -> consultation_flow_runs`
- `assessment_sessions -> assessment_flow_runs`
- `multimodal_sessions -> multimodal_flow_sessions`
- `multimodal_captures -> multimodal_samples`
- `multimodal_inference_results -> multimodal_observations`
- `multimodal_turn_bundles -> multimodal_turn_summaries`
- `consultation_turn_id -> turn_id`
- `consultation_session_id -> consultation_flow_run_id`
- `prompt_key -> question_key`
- `frame_index -> sample_index`

### 本步是否改数据库

不改。

### 本步是否改代码

不改。

### 本步完成标志

满足这两个条件才算完成：

1. 每张旧表都知道未来是保留、重命名还是拆分。
2. 每个旧字段都知道未来是保留、替换还是删除。

## Step 3：开始改数据库，只做加法迁移

### 目标

先把新主链需要的表和字段加出来，但不删旧字段，不断旧逻辑。

### 从这一步开始，允许改数据库表

是。

### 本步要做什么

#### 3.1 新增顶层表

新增 `encounter_sessions`：

- `id`
- `user_id`
- `entry_flow_type`
- `current_flow_type`
- `status`
- `started_at`
- `completed_at`
- `created_at`
- `updated_at`

#### 3.2 在现有流程表上加外键字段

给 `consultation_sessions` 新增：

- `encounter_session_id`

给 `assessment_sessions` 新增：

- `encounter_session_id`
- `source_consultation_flow_run_id`

#### 3.3 在 multimodal 表上加新作用域字段

给 `multimodal_sessions` 新增：

- `encounter_session_id`
- `flow_type`
- `flow_run_id`
- `live_state_payload`

给 `multimodal_captures` 新增：

- `turn_id`
- `flow_run_id`
- `stage_id`
- `question_key`
- `sample_index`
- `sample_started_at`
- `sample_ended_at`

给 `multimodal_inference_results` 新增：

- `turn_id`
- `flow_run_id`
- `stage_id`
- `question_key`
- `sample_id`

给 `multimodal_turn_bundles` 新增：

- `turn_id`
- `flow_run_id`
- `stage_id`
- `question_key`

#### 3.4 在 `consultation_turns` 上加新字段

新增：

- `encounter_session_id`
- `consultation_flow_run_id`
- `question_key`
- `question_order`
- `question_video_asset_id`
- `question_video_uri`
- `question_text`
- `question_subtitle_text`
- `turn_window_started_at`
- `turn_window_completed_at`
- `turn_summary_payload`

### 本步暂时不做什么

- 不删 `workflow_stage_id`
- 不删 `consultation_turn_id`
- 不删 `prompt_key`
- 不删 `frame_index`
- 不删 `session_summary_payload`

### 本步是否改代码

只允许改 Alembic 和 model 定义，不改业务链路。

## Step 4：开始改代码写路径，做双写

### 目标

让新字段开始被真实写入，但旧逻辑仍然可跑。

### 从这一步开始，允许改代码

是。

### 本步要做什么

#### 4.1 consultation 创建时同时创建 `encounter_session`

调整 `consultation-service`：

- 创建 `consultation_session` 前先创建 `encounter_session`
- 将 `consultation_session.encounter_session_id` 写上去

#### 4.2 assessment 创建时挂到同一个 encounter

调整 `assessment-service`：

- 创建 `assessment_session` 时带上 `encounter_session_id`
- 同时写 `source_consultation_flow_run_id`

#### 4.3 multimodal session 创建时不再只靠 owner 语义

调整 `multimodal-service` 和 `consultation-service` 调用链：

- 创建 `multimodal_session` 时双写：
  - 旧字段：`owner_service`、`owner_session_id`
  - 新字段：`encounter_session_id`、`flow_type`、`flow_run_id`

#### 4.4 回答窗口开始时就生成 `turn_id`

这是整个重构的第一个关键代码改动。

调整前端和 consultation 状态机：

- 不再在录音完成时生成 `turn_id`
- 改成进入 `waiting_user_input` 时就生成 `turn_id`
- 当前回答窗口内所有 face / pose / eeg sample 都绑定该 `turn_id`

#### 4.5 连续模态写入新字段

调整 `multimodal-service`：

- face / pose / eeg 写 sample 时同时写：
  - `turn_id`
  - `flow_run_id`
  - `stage_id`
  - `question_key`
  - `sample_index`

### 本步是否改数据库

不再新增大块表结构，只允许补索引或默认值。

## Step 5：切换读取口径

### 目标

让读路径开始以新字段为主，旧字段为兼容兜底。

### 本步要做什么

#### 5.1 consultation / assessment 读路径切新口径

- 对外返回 `encounter_session_id`
- 对内统一使用 `consultation_flow_run_id`、`assessment_flow_run_id`

#### 5.2 multimodal live 只读 `live_state_payload`

- 实时看板只依赖 `live_state_payload`
- 不再依赖 `session_summary_payload`

#### 5.3 turn 汇总切到新 turn 作用域

- `turn_summary_payload` 改为从当前 `turn_id` 下全部 sample 聚合
- face / pose / eeg 不再按单帧思路拼 turn 结果
- turn 级连续模态只存：
  - `sample_count`
  - `valid_sample_count`
  - `label_distribution`
  - `quality_distribution`

### 本步是否改数据库

通常不需要再改表结构。

### 本步是否改代码

是，这一步是读逻辑和聚合逻辑切换的主阶段。

## Step 6：停写旧字段

### 目标

当新字段已经稳定后，停止向旧字段写入。

### 本步要做什么

停止写这些旧字段：

- `consultation_turn_id`
- `consultation_session_id`
- `prompt_key`
- `frame_index`
- `capture_started_at`
- `capture_ended_at`
- `session_summary_payload`

同时把代码里的命名改成新口径：

- `consultation_turn_id -> turn_id`
- `prompt_key -> question_key`
- `frame_index -> sample_index`

### 本步是否改数据库

不删字段，只停写。

### 本步是否改代码

是。

## Step 7：清理旧运行数据并停掉兼容层

### 目标

既然本次重构不保留旧的问诊 / 量表 / 多模态运行数据，那这一步不再做历史回填，
而是直接清理旧运行数据，并把代码里的旧输入兼容和旧字段桥接停掉。

### 本步要做什么

- 清理本次重构涉及的旧运行数据：
  - `consultation_sessions` 相关运行态业务数据
  - `consultation_turns`
  - `assessment_sessions`、`assessment_answers`、`assessment_results`
  - `multimodal_sessions`
  - `multimodal_audio_turns`
  - `multimodal_captures`
  - `multimodal_inference_results`
  - `multimodal_turn_bundles`
- 保留账号、权限、配置、字典、流程定义等基础数据，不做全库清空。
- 停掉代码里的旧字段输入兼容：
  - `consultation_turn_id -> turn_id`
  - `consultation_session_id -> flow_run_id`
  - `capture_started_at -> sample_started_at`
  - `capture_ended_at -> sample_ended_at`
  - `frame_index -> sample_index`
- 停掉路由和 service 里的旧 fallback：
  - audio 路由不再接受旧 `consultation_session_id`
  - `multimodal` schema 不再接受旧字段别名
  - consultation / assessment / multimodal 内部不再桥接旧命名
- 把还残留在旧列上的主链补齐到新列，尤其是 audio 这条链路。

### 本步是否改数据库

可以执行清数脚本、一次性数据清理脚本和小范围兼容收口迁移，
但这一阶段不做大规模删列。

### 本步是否改代码

允许改代码，目标是把系统切到“只认新口径”的运行态。

## Step 8：删除旧字段、旧约束和旧命名

### 目标

在新链路稳定后，真正收口 schema。

### 本步要做什么

删除旧字段和旧语义：

- `owner_service`
- `owner_session_id`
- `consultation_turn_id`
- `consultation_session_id`
- `prompt_key`
- `frame_index`
- `capture_started_at`
- `capture_ended_at`
- `session_summary_payload`

同时删除旧索引、旧唯一约束、旧兼容列约束，例如：

- `uq_multimodal_turn_bundles_session_turn`
- 各表围绕 `consultation_turn_id` / `consultation_session_id` 的旧索引
- 只为兼容停写阶段保留的旧列可空约束调整

必要时执行表重命名：

- `consultation_sessions -> consultation_flow_runs`
- `assessment_sessions -> assessment_flow_runs`
- `multimodal_sessions -> multimodal_flow_sessions`
- `multimodal_captures -> multimodal_samples`
- `multimodal_inference_results -> multimodal_observations`
- `multimodal_turn_bundles -> multimodal_turn_summaries`

当前实现说明：

- Step 8 已经完成旧列、旧索引、旧约束删除，但**没有执行物理表重命名**。
- 这是有意保留，不是遗漏。当前判断是：
  - 表名只影响内部 schema，可读性收益有限
  - 涉及 Alembic、ORM、跨服务 SQL、运维排查口径，破坏面更大
  - 在主链已经稳定、对外字段已切新口径的前提下，物理表重命名不是当前必要动作
- 如果后续要做表重命名，应作为**单独一轮 schema 工程**处理，不与业务链路改动混做。

### 本步是否改数据库

是。这是唯一允许做破坏性删改的阶段。

### 本步是否改代码

是，需要同步删兼容分支。

## 5. 哪一步开始改数据库，哪一步开始改代码

### 先回答最直接的问题

#### 第一步要干嘛？

先做 **Step 1：冻结目标口径**。

#### 第二步要干嘛？

再做 **Step 2：做旧表到新口径的映射清单**。

#### 哪一步开始改数据库表？

从 **Step 3** 开始。

#### 哪一步开始改业务代码？

从 **Step 4** 开始。

#### 哪一步开始改聚合逻辑和读路径？

从 **Step 5** 开始。

#### 哪一步才能删旧字段？

到 **Step 8** 才能删。

## 6. 推荐实施节奏

如果按实际开发效率排，我建议这样推进：

1. `Step 1 + Step 2` 一次完成  
2. `Step 3` 单独做一次数据库迁移  
3. `Step 4` 先只改 `consultation + multimodal` 主链  
4. `Step 5` 切 live 和 turn summary  
5. `Step 6 + Step 7` 做兼容停写、清理旧运行数据、切断旧 fallback  
6. `Step 8` 最后删旧列、删旧约束并收口

## 7. 后续执行约束

从这份文档开始，后面实际改代码时遵守两个约束：

1. 每一轮改动只跨一个阶段，不要同时做加字段、改写路径、删旧字段。
2. 每完成一个阶段，都先验证 consultation 主链可跑，再进入下一阶段。
