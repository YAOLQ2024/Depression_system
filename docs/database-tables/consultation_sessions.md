# `consultation_sessions` 表说明

## 1. 表作用

`consultation_sessions` 是规则式数字问诊的主会话表，用来保存“一次完整问诊”的当前状态、上下文快照、阶段结果以及量表阶段移交的数据。

它既是流程状态表，也是问诊摘要表。系统通过它恢复当前问到哪一题、判断是否进入高风险人工复核、以及生成后续量表评估需要的移交载荷。

## 2. 在系统哪一步使用

1. 问诊会话创建：`POST /api/v1/consultations` 时创建草稿会话，写入用户资料快照、设备与同意状态、默认医生 persona。
2. 问诊启动：`POST /api/v1/consultations/{session_id}/start` 时更新 `started_at`、推进到首个等待节点。
3. 问候与流程说明阶段：依赖 `context_snapshot`、`current_stage_id`、`current_node_id`、当前播放问题项字段推进流程。
4. 主诉采集阶段：保存 `chief_complaint_raw_text`、`chief_complaint_summary`，并把抽取结果写入 `slot_values`。
5. 现病史追问阶段：把逐轮抽取出的槽位累计到 `slot_values`，并生成 `current_history_structured_result`。
6. 高风险筛查阶段：生成 `high_risk_screening_result`，必要时把 `requires_human_review` 置为 `true`。
7. 问诊结束与量表移交：生成 `scale_handoff_payload`，把 `workflow_stage_id` 切到量表或人工决策阶段，并写入 `completed_at`。

## 3. 字段说明

| 字段名 | 英文翻译 | 中文翻译 | 类型/约束 | 作用 | 为什么需要这个字段 | 主要使用步骤 |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | Consultation Session ID | 问诊会话ID | `String(36)`，主键 | 唯一标识一次问诊会话。 | 问诊是长流程，必须有稳定主键供前端、gateway、量表服务继续引用。 | 会话创建、状态查询、后续量表关联 |
| `user_id` | User ID | 用户ID | `String(64)`，索引，非空 | 标识这次问诊属于哪位用户。 | 服务需要校验“当前登录用户只能访问自己的问诊会话”。 | 会话创建、权限校验、状态查询 |
| `workflow_id` | Workflow ID | 工作流ID | `String(128)`，非空 | 标识当前使用的是哪套问诊工作流。 | 后续若存在多个问诊版本，需要靠它区分执行逻辑和回放依据。 | 会话创建、问诊回放、排障 |
| `script_bundle` | Script Bundle | 剧本包标识 | `String(128)`，非空 | 标识当前绑定的剧本资源集合。 | 工作流骨架与具体剧本资源可能演进不同步，需要单独记录。 | 会话创建、回放、资源定位 |
| `playlist_version` | Playlist Version | 数字人播放清单版本 | `String(128)`，可空 | 记录当前数字人视频问题清单版本。 | 同一个工作流在不同版本下可能对应不同素材，必须保留版本信息保证可追溯。 | 会话创建、当前问题展示、回放 |
| `workflow_stage_id` | Workflow Stage ID | 工作流阶段ID | `String(128)`，非空 | 记录当前问诊处于更高层级的业务阶段，如问诊主链、人工决策、量表阶段。 | 需要把“问诊内部子阶段”和“跨服务业务阶段”区分开，便于网关与下游服务衔接。 | 问诊中、高风险分流、量表移交 |
| `current_stage_id` | Current Stage ID | 当前子阶段ID | `String(128)`，可空 | 记录当前正处于哪个固定问诊子阶段。 | 没有它就无法从中断点继续推进四个固定子模块。 | 问候阶段、主诉阶段、现病史阶段、高风险阶段 |
| `current_node_id` | Current Node ID | 当前节点ID | `String(128)`，可空 | 记录当前脚本节点位置。 | 同一阶段里包含多个节点，恢复执行时必须知道精确停在哪个节点。 | 问诊进行中、恢复执行 |
| `current_question_key` | Current Question Key | 当前问题键 | `String(128)`，可空 | 缓存当前数字人问题项的键值。 | 前端播放结束上报 `question_key` 时，需要与数据库中的当前问题键做一致性校验。 | 问题展示、系统视频完成上报 |
| `current_question_order` | Current Question Order | 当前问题顺序号 | `Integer`，可空 | 记录当前问题在播放清单中的顺序。 | 前端进度条和回放顺序需要稳定顺序号，而不能只依赖文本。 | 问题展示、进度计算 |
| `current_question_video_asset_id` | Current Question Video Asset ID | 当前视频素材ID | `String(128)`，可空 | 指向当前问题对应的视频素材标识。 | 便于前端或素材服务定位具体视频资源，也便于回放与审计。 | 问题展示、素材定位 |
| `current_question_video_uri` | Current Question Video URI | 当前视频地址 | `Text`，可空 | 保存当前问题对应视频的可播放地址。 | 前端需要直接拿到 URI 播放，不必每次再从资源清单反查。 | 问题展示 |
| `current_question_text` | Current Question Text | 当前问题文案 | `Text`，可空 | 保存当前问题的标准提问文本。 | 前端、字幕栏和审计日志都需要明确知道系统在问什么。 | 问题展示、回放 |
| `current_question_subtitle_text` | Current Question Subtitle Text | 当前字幕文案 | `Text`，可空 | 保存当前问题的字幕文本。 | 字幕和口播文案不一定完全相同，单独保存可支持无障碍和多终端展示。 | 问题展示 |
| `total_prompt_count` | Total Prompt Count | 总问题项数量 | `Integer`，非空 | 记录本次问诊总共需要播放多少个固定问题项。 | 前端显示总进度和后端判断完成比例都需要该基数。 | 会话创建、进度展示 |
| `completed_prompt_count` | Completed Prompt Count | 已完成问题项数量 | `Integer`，非空 | 记录当前已经完成的固定问题项数。 | 用于构建进度条和估算用户当前所处位置。 | 问诊进行中、进度展示 |
| `status` | Session Status | 会话状态 | `String(64)`，索引，非空 | 保存当前会话状态，如 `draft`、`waiting_user_input`、`handoff_ready`。 | 外部系统需要快速判断会话是否可启动、是否等待用户、是否已经准备好移交。 | 全流程 |
| `assigned_doctor_persona` | Assigned Doctor Persona | 绑定医生人设 | `String(128)`，非空 | 记录当前问诊绑定的数字医生 persona。 | 问诊文案、形象和语气需要可追溯，避免后续回放时找不到使用的是哪位“医生”。 | 会话创建、问诊展示、回放 |
| `requires_human_review` | Requires Human Review | 是否需要人工复核 | `Boolean`，非空 | 标记是否触发了高风险人工介入。 | 高风险不能直接继续标准量表主链，需要一个明确开关阻断自动流转。 | 高风险筛查、人工分流 |
| `participant_profile_snapshot` | Participant Profile Snapshot | 受试者资料快照 | `JSON`，非空 | 保存问诊开始时收到的用户基础资料快照。 | 如果用户之后修改了资料，历史问诊仍应保留当时的真实上下文。 | 会话创建、问候阶段、问诊回放 |
| `context_snapshot` | Context Snapshot | 上下文快照 | `JSON`，非空 | 保存音频通道、同意状态、设备状态、准备状态等上下文。 | `system_gate` 节点需要检查这些前置条件，且后续排障要知道当时环境是否就绪。 | 会话创建、问候阶段、系统前置检查 |
| `slot_values` | Slot Values | 槽位值集合 | `JSON`，非空 | 保存各轮问答抽取出的结构化槽位。 | 规则路由、模板提问、阶段摘要都依赖累计槽位，不能只看最后一轮输入。 | 主诉采集、现病史追问、高风险判断 |
| `engine_state` | Engine State | 引擎状态快照 | `JSON`，非空 | 保存当前提示词、等待节点类型、已完成阶段、上一次分支结果等内部状态。 | 规则引擎需要能够恢复执行，而不是每次重新从头推导整条链路。 | 问诊启动、每轮推进、异常恢复 |
| `chief_complaint_raw_text` | Chief Complaint Raw Text | 主诉原始文本 | `Text`，可空 | 保存患者主诉的原始表达。 | 原始主诉是后续摘要、审计和人工复核的重要依据，不能只保留摘要。 | 主诉采集 |
| `chief_complaint_summary` | Chief Complaint Summary | 主诉摘要 | `Text`，可空 | 保存从主诉中提炼出的简短摘要。 | 下游量表、风险和展示层更适合消费摘要，而不是每次处理整段原文。 | 主诉采集、问诊状态展示、量表移交 |
| `current_history_structured_result` | Current History Structured Result | 现病史结构化结果 | `JSON`，可空 | 保存现病史阶段汇总后的结构化字段结果。 | 后续判断和移交需要阶段级结果，不能靠逐轮 turn 现场拼装。 | 现病史阶段结束、量表移交 |
| `high_risk_screening_result` | High Risk Screening Result | 高风险筛查结果 | `JSON`，可空 | 保存自杀意念、自伤行为、计划、支持状态和风险级别等结果。 | 安全门决策必须有明确可审计的结构化输出。 | 高风险筛查、人工复核、量表是否放行 |
| `scale_handoff_payload` | Scale Handoff Payload | 量表移交载荷 | `JSON`，可空 | 保存问诊结束后传给 `assessment-service` 的汇总数据。 | 跨服务不能依赖重新回算问诊结果，需要一次性产出稳定移交对象。 | 问诊结束、量表会话创建 |
| `started_at` | Started Time | 开始时间 | `DateTime(timezone=True)`，可空 | 记录问诊正式开始时间。 | 需要区分“已创建草稿”与“用户真的开始问诊”的时间。 | 问诊启动、时长统计 |
| `completed_at` | Completed Time | 完成时间 | `DateTime(timezone=True)`，可空 | 记录问诊主链结束时间。 | 便于判断问诊是否已完成，以及计算总耗时。 | 高风险结束或量表移交前 |
| `created_at` | Created Time | 创建时间 | `DateTime(timezone=True)`，非空 | 记录会话创建时间。 | 需要审计和排序，也能区分同一用户的多次问诊。 | 会话创建、列表排序 |
| `updated_at` | Updated Time | 更新时间 | `DateTime(timezone=True)`，非空 | 记录最近一次状态推进时间。 | 前端轮询、缓存更新和排障都需要知道会话何时最后变化。 | 全流程 |

## 4. 备注

- 这张表是问诊域里最核心的“状态源”，很多前端展示字段其实都是从这里直接返回的。
- `current_question_*` 一组字段属于“冗余但必要”的缓存字段，目的是降低前端展示和服务回放时对资源文件二次解析的依赖。
