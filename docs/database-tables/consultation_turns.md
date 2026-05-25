# `consultation_turns` 表说明

## 1. 表作用

`consultation_turns` 用来记录问诊过程中的“逐轮交互明细”。如果说 `consultation_sessions` 保存的是整场问诊的当前状态和阶段结果，那么 `consultation_turns` 保存的就是每一轮问答发生了什么。

这张表主要用于：

- 审计和回放每一轮对话
- 记录患者原始输入与转写结果
- 记录当前轮抽取出的结构化字段
- 记录是正常回答、沉默还是识别失败

## 2. 在系统哪一步使用

1. 主诉采集阶段：每次患者回答主诉问题时写入一条 turn。
2. 症状筛查规则问诊阶段：每轮追问都写入 turn，并保存抽取字段。
3. 高风险问题排查阶段：每轮安全相关回答都写入 turn。
4. 事后回放与审计：用于还原用户当时看到的问题、给出的回答、触发的分支和回答时长。

## 3. 字段说明

| 字段名 | 英文翻译 | 中文翻译 | 类型/约束 | 作用 | 为什么需要这个字段 | 主要使用步骤 |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | Consultation Turn ID | 问诊轮次ID | `String(36)`，主键 | 唯一标识一轮用户输入。 | 一次会话包含多轮记录，必须对每轮有单独主键以支持追踪和排障。 | 每轮提交 |
| `session_id` | Session ID | 所属会话ID | `String(36)`，外键到 `consultation_sessions.id`，索引，非空 | 指明这条 turn 属于哪场问诊。 | 没有会话外键就无法把多轮记录归并回同一场问诊。 | 每轮提交、回放 |
| `workflow_stage_id` | Workflow Stage ID | 工作流阶段ID | `String(128)`，非空 | 记录该轮发生时所处的高层工作流阶段。 | 当会话后续切到量表或人工决策阶段时，仍能知道这轮对话发生在问诊主链的哪个业务层级。 | 回放、审计 |
| `stage_id` | Stage ID | 子阶段ID | `String(128)`，非空 | 记录该轮属于哪个问诊子阶段。 | 需要区分主诉、症状筛查、高风险等不同阶段的回答。 | 主诉采集、症状筛查追问、高风险筛查 |
| `node_id` | Node ID | 节点ID | `String(128)`，非空 | 记录当时执行到的具体脚本节点。 | 同一阶段可能有多个节点，排障时必须精确到具体节点。 | 每轮提交、回放 |
| `turn_index` | Turn Index | 轮次序号 | `Integer`，可空 | 表示本场问诊中的第几轮用户输入。 | 排序和展示对话历史时，稳定的顺序号比仅依赖时间更可靠。 | 每轮提交、历史展示 |
| `prompt_key` | Prompt Key | 问题键 | `String(128)`，可空 | 记录本轮问题对应的固定问题项键值。 | 前后端都需要知道“用户回答的是哪一道系统问题”。 | 回放、前端映射 |
| `prompt_order` | Prompt Order | 问题顺序号 | `Integer`，可空 | 记录本轮问题在问题清单中的顺序。 | 便于做进度对齐、回放排序和行为分析。 | 回放、进度分析 |
| `prompt_video_asset_id` | Prompt Video Asset ID | 问题视频素材ID | `String(128)`，可空 | 保存这轮问题对应的视频素材标识。 | 审计时需要知道用户当时看到的是哪段视频素材。 | 回放、素材审计 |
| `prompt_video_uri` | Prompt Video URI | 问题视频地址 | `Text`，可空 | 保存问题视频地址。 | 回放时可以直接重建展示环境，不必再次解析资源文件。 | 回放 |
| `prompt_question_text` | Prompt Question Text | 问题文本 | `Text`，可空 | 保存这一轮系统实际提出的问题文本。 | 同一节点文案未来可能变更，落库后可还原历史真实问题。 | 回放、人工复核 |
| `prompt_subtitle_text` | Prompt Subtitle Text | 问题字幕文本 | `Text`，可空 | 保存字幕用文本。 | 字幕与口播不完全一致时，需要单独保留以支持无障碍和前端一致展示。 | 回放、前端展示 |
| `input_type` | Input Type | 输入类型 | `String(64)`，非空 | 标记本轮输入来自语音、手动输入、继续按钮、沉默或识别失败。 | 服务的分支逻辑直接依赖输入类型，不能只看文本内容。 | 每轮提交、分支判断 |
| `prompt_text` | Rendered Prompt Text | 渲染后的提示词文本 | `Text`，可空 | 保存本轮等待用户回答前，服务真正渲染出的提示词。 | 模板变量替换后才是用户真实听到的问题，回放时需要保存最终版本。 | 每轮提交、回放 |
| `raw_input` | Raw Input | 原始输入 | `Text`，可空 | 保存客户端上传的原始回答文本或原始兜底输入。 | 需要保留未经服务清洗的第一手输入，便于比对转写误差。 | 每轮提交、审计 |
| `transcript_text` | Transcript Text | 转写文本 | `Text`，可空 | 保存语音识别后的文本。 | 规则抽取和文本归一化通常基于转写结果，需要单独存档。 | 每轮提交、规则抽取 |
| `structured_fields` | Structured Fields | 结构化抽取字段 | `JSON`，可空 | 保存本轮从回答中抽取出的结构化字段。 | 如果只把结果累计到 `slot_values`，会失去“这一轮具体贡献了什么”的可追踪性。 | 主诉采集、症状筛查追问、高风险筛查 |
| `branch_taken` | Branch Taken | 触发分支 | `String(64)`，非空 | 记录这轮命中了哪个分支，例如 `normal`、`silence`、`recognition_failure`。 | 流程为什么会跳到某个后继节点，必须有明确分支证据。 | 每轮提交、流程排障 |
| `response_started_at` | Response Started Time | 作答开始时间 | `DateTime(timezone=True)`，可空 | 记录用户开始作答的时间。 | 便于分析用户反应时长，也能支持多模态时间对齐。 | 每轮提交、时序分析 |
| `response_completed_at` | Response Completed Time | 作答完成时间 | `DateTime(timezone=True)`，可空 | 记录用户完成作答的时间。 | 需要计算回答耗时，判断中途停顿或超时。 | 每轮提交、时序分析 |
| `created_at` | Created Time | 落库时间 | `DateTime(timezone=True)`，非空 | 记录该轮记录写入数据库的时间。 | 需要知道数据真正入库的时刻，方便排查客户端与服务端时间差。 | 每轮提交、审计 |

## 4. 备注

- 当前代码只在“需要用户输入的轮次”写入本表；纯系统视频播放完成不会新增 turn。
- `structured_fields` 与 `slot_values` 的关系是：前者保存“单轮产出”，后者保存“会话累计结果”。
