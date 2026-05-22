# 语音情绪识别接入系统的代码对齐版实施方案

## 1. 文档目标

本文档只聚焦一个模态：

- `speech`

目标不是重新设计一套脱离现代码的新架构，而是基于当前 `depression-system` 已经存在的前后端链路，整理出一版可直接指导实施、联调和验收的语音模态方案。

本文档重点回答四件事：

1. 当前代码里的语音链路到底怎么跑
2. 语音模态结果现在落在哪里
3. 语音模态和 `live / bundle / turn` 的关系是什么
4. 下一步应该怎么补齐成稳定的正式方案

本文档不展开：

- face / pose 的详细推理设计
- EEG 接入
- 风险服务融合策略
- 模型训练与评测细节

---

## 2. 当前代码中的真实定位

当前系统里，语音模态已经不是“待设计状态”，而是已经有一条可以工作的主链。

这条主链的核心特征是：

- 浏览器前端直接访问 `:18080/api/v1`
- 语音原始文件先进入 `multimodal-service`
- `multimodal-service` 负责音频标准化、ASR、语音情绪推理、会话级 `live` 更新、轮次级 `bundle` 聚合
- `consultation-service` 负责正式业务 `turn` 落库
- 前端在拿到最终转写后，再提交正式问诊回答

这意味着当前实现并不是：

- 前端直接把音频提交给 `consultation-service`
- `consultation-service` 再统一处理音频、对象存储、ASR、语音情绪
- 再单独落一张 `speech_emotion_results` 表

因此，后续语音方案必须建立在现有多模态骨架上，而不是另起一套单模态专用存储和接口。

---

## 3. 当前语音模态端到端流程

### 3.1 前端采集与上传

问诊页在用户完成一轮录音后，会把音频上传到 `multimodal-service` 的 `audio-turn` 入口，而不是先提交到 `consultation-service`。

当前前端真实流程可以概括为：

1. 用户开始录音
2. 浏览器采集整段回答音频
3. 用户结束录音
4. 前端调用 `uploadMultimodalAudioTurn`
5. 前端轮询 `getMultimodalAudioTurn`
6. 等待 `multimodal-service` 返回最终转写和语音模态状态
7. 前端再调用 `submitConsultationTurn`
8. 把正式 `transcript_text`、`audio_uri` 等业务真相写入 `consultation-service`

所以当前系统里的“语音回答提交”实际上是两段式：

- 第一段：多模态处理
- 第二段：业务 turn 持久化

### 3.2 multimodal-service 的职责

`multimodal-service` 当前负责：

1. 接收本轮音频
2. 生成标准化音频
3. 调用 Dolphin ASR
4. 调用语音情绪识别
5. 写入 capture / inference 相关记录
6. 更新会话级 `live`
7. 在有 `turn_id` 的情况下聚合 turn 级 `bundle`

换句话说，语音模态当前已经天然属于“统一多模态服务”的职责域，而不是 `consultation-service` 的本地附属逻辑。

### 3.3 consultation-service 的职责

`consultation-service` 当前不负责音频推理本身，它负责的是问诊业务真相。

语音链路里它的职责是：

1. 保存正式业务 `turn`
2. 保存 `audio_uri`
3. 保存 `transcript_text`
4. 保存 `transcript_source`
5. 缓存 turn 级的 `turn_summary_payload`
6. 对外提供 consultation session / turn 查询能力

因此可以把它理解成：

- `multimodal-service` 负责模态事实
- `consultation-service` 负责问诊业务事实

---

## 4. 当前语音数据到底存在哪

当前代码已经形成了四层数据结构，语音模态也应沿用这四层，不建议再引入独立的 `speech_emotion_results` 主表。

### 4.1 capture

`capture` 表示一次原始模态输入事件。

对语音来说，可以理解为：

- 本轮上传的一段音频
- 它是后续 ASR 和语音情绪推理的输入源

### 4.2 inference result

`inference result` 表示某个模态模型的一次推理输出。

对语音来说，至少会包含：

- 主情绪标签
- 主分数
- Top-K
- 时间戳
- 状态

### 4.3 live

`live` 是会话级最新快照。

对语音来说，它表示：

- 当前这个 consultation session 最近一次可用的语音模态结果是什么

它的典型用途是：

- 前端右侧状态面板实时展示
- 当前会话最新状态刷新

### 4.4 bundle

`bundle` 是 turn 级聚合快照。

对语音来说，它表示：

- 某个 `turn_id` 的最终语音模态归档结果

它的典型用途是：

- 单轮回顾
- 复盘
- 后续多模态融合
- turn 级落库缓存

---

## 5. 语音模态与 live / bundle / turn 的关系

这一段是本方案最关键的认知边界。

### 5.1 turn 是业务真相

`turn` 表示患者对某一道题的一次正式回答。

它保存的是业务主语义，例如：

- `question_key`
- `stage_id`
- `input_type`
- `audio_uri`
- `transcript_text`
- `transcript_source`

也就是说：

- `turn` 不是模态推理容器
- `turn` 是问诊业务主记录

### 5.2 live 是会话级最新态

`live` 不关心某一轮历史细节，只关心“现在最新是什么”。

对语音来说：

- 本轮刚处理完成后，`live.audio` 会刷新成最新结果
- 下一轮再完成时，旧值会被覆盖

所以：

- `live` 适合状态面板
- `live` 不适合作为完整历史归档

### 5.3 bundle 是轮次级最终态

`bundle` 关心的是“某一轮最终保留什么”。

对语音来说：

- 当本轮结果确定后，把语音特征和结果写入该 `turn_id` 的 bundle
- 后续页面回看、后端复盘、风险融合都应该优先读 bundle

所以：

- `bundle` 是按 turn 归档的
- `bundle` 比 `live` 更稳定、更适合后续正式消费

### 5.4 一句话总结

可以直接这样理解：

- `turn = 业务真相`
- `live = 当前最新展示态`
- `bundle = 单轮最终归档态`

---

## 6. 当前方案与旧版文档的差异

为了避免后续继续按旧假设开发，这里明确列出必须修正的点。

### 6.1 不再建议新增 `speech_emotion_results` 主表

旧思路里单独新增 `speech_emotion_results` 表，这在“只有语音一个模态”的早期阶段可以理解，但和当前系统已经存在的多模态统一骨架不一致。

当前更合理的方式是继续复用：

- `multimodal_captures`
- `multimodal_inference_results`
- `multimodal_turn_bundles`
- session `live_state_payload`

必要时只在 `consultation_turn.turn_summary_payload` 做缓存，不再为语音单独造一套正式主存储。

### 6.2 不再把 `consultation-service` 作为音频上传主入口

当前真实实现里，前端并不是：

- `POST /consultations/{session_id}/turns/audio`

而是先打 `multimodal-service` 的 `audio-turns` 相关接口。

因此后续如果要补正式文档、接口图、联调文档，都要按当前真实调用顺序来写，不能再以“consultation-service 收原始音频”为主叙事。

### 6.3 当前前端已经依赖轮询

旧设计里强调“不要轮询、同步一次返回最终结果”，这更像理想化的单接口闭环。

但当前代码已经是：

- 上传 audio-turn
- 轮询 audio-turn 状态
- 获取 transcript
- 再提交正式 consultation turn

因此第一阶段不应强行推翻轮询链路，而应先承认并稳定它。

### 6.4 文本模态已经和语音链路产生耦合

当前语音上传后，`multimodal-service` 不仅做语音情绪，还会利用最终转写文本产出文本情绪结果。

因此语音模态方案不能再把文本排除成“后续无关项”，至少需要承认：

- speech 和 speech-transcript text 在当前实现里是同一条处理链上的相邻产物

---

## 7. 当前代码对齐后的语音最小实施方案

基于当前代码，语音模态最小正式方案建议保持如下原则。

### 7.1 保持两段式链路，不重写为单入口

第一阶段不要强推成“前端只调一个接口”。

建议继续沿用当前两段式结构：

1. 前端上传音频到 `multimodal-service`
2. `multimodal-service` 完成 ASR 和 speech emotion
3. 前端拿到正式 transcript 后提交 `consultation_turn`

这条链路已经存在，改动面最小。

### 7.2 把语音结果正式定义为 multimodal 标准结果

语音结果建议统一成多模态标准结构，而不是裸露模型原始输出。

建议至少统一成：

- `primary_label`
- `primary_score`
- `top_3_labels`
- `captured_at`
- `status`
- `source = audio`

这样前端、bundle、live、后续融合都可以复用相同契约。

### 7.3 live 只负责展示最新结果

右侧状态面板读取语音时，应优先读会话级 `live.audio`。

它的职责只包括：

- 当前状态
- 当前主标签
- 必要的简要分数信息

不把它当作正式历史查询源。

### 7.4 bundle 作为单轮正式归档

每个 `turn_id` 最终应该有一份稳定的 bundle 结果。

语音模态应把最终使用价值沉淀在：

- `turn_bundle.audio_features`

而不是依赖前端内存态或只依赖 `live`。

### 7.5 consultation_turn 保存正式业务音频与转写

`consultation_turn` 应继续承担语音业务真相落库：

- `audio_uri`
- `transcript_text`
- `transcript_source`

这样后续问诊链路、导出、审计、风险处理都还能以业务 turn 为中心工作。

---

## 8. 当前阶段需要补齐的缺口

语音主链已经基本成型，但要变成“稳定正式方案”，还建议补齐下面几个点。

### 8.1 明确标准化音频对象的留档策略

当前文档层面需要明确：

- 原始音频是否长期保存
- 标准化 wav 是否长期保存
- 两者的对象存储命名规范是什么
- 是否都需要在业务侧可追溯

建议保留两层对象：

- 原始上传音频
- 标准化模型输入音频

### 8.2 固定语音模态对外结果契约

现在模型原始输出可以变化，但系统内字段不应该反复变化。

建议固定至少这几个字段：

- `primary_label`
- `primary_score`
- `top_3_labels`
- `status`
- `captured_at`

如果当前接口返回的是模型原始字段，也建议逐步在服务层做标准化。

### 8.3 明确 audio-turn 完成态与 consultation-turn 提交时机

当前链路里前端会先等音频转写完成，再提交 consultation turn。

文档上应明确：

- 什么叫 audio-turn 已完成
- 是否以 transcript 完成作为完成标准
- speech emotion 失败时 consultation turn 是否仍允许提交
- 文本结果未产出时 consultation turn 是否阻塞

这几个时序边界必须写清楚，否则联调时最容易分歧。

### 8.4 明确失败状态的展示和回写策略

语音模态至少要区分：

- 上传失败
- 标准化失败
- ASR 失败
- speech emotion 失败

同时要明确：

- `live` 怎么表现失败
- `bundle` 是否保留失败状态
- `consultation_turn` 是否仍然允许保存基础音频记录

---

## 9. 推荐的分阶段落地顺序

### Step 1：先冻结当前语音链路的数据契约

优先确认并写死：

- audio-turn 请求字段
- audio-turn 返回字段
- speech emotion 标准输出结构
- consultation turn 提交字段
- bundle 中 audio_features 的正式字段名

### Step 2：补齐语音结果的状态定义

建议统一至少三态：

- `processing`
- `completed`
- `failed`

必要时补：

- `partial`
- `transcript_ready`

但第一阶段不要过度复杂化。

### Step 3：明确 live 和 bundle 的读写边界

建议在文档和代码里都统一：

- `live` 给看板
- `bundle` 给单轮复盘和后续消费
- `consultation_turn` 给业务主真相

这样后续 text / face / pose 接入时不会每个模态都重新发明一遍。

### Step 4：补齐页面刷新后的恢复策略

当前前端除实时状态外，还需要保证刷新页面后：

- 能恢复 consultation turn
- 能恢复本轮 bundle
- 能恢复当前 session live

否则语音模态只是“运行时可见”，不是“正式系统状态”。

### Step 5：补齐联调验收清单

验收建议至少覆盖：

1. 浏览器能正常录音并上传
2. `multimodal-service` 能成功创建 audio-turn
3. ASR 能返回正式 transcript
4. speech emotion 能返回标准化结果
5. `live.audio` 能更新
6. consultation turn 能写入 `audio_uri` 和 `transcript_text`
7. turn bundle 能包含 `audio_features`
8. 页面刷新后语音结果仍可恢复

---

## 10. 建议保留的总体原则

即使当前代码不是最理想形态，也建议坚持以下原则不变：

1. 一轮回答对应一个最终语音结果
2. 语音情绪判断优先基于整轮音频，而不是高频切片
3. 业务真相和模态真相分层保存
4. 先保证 `live / bundle / turn` 一致，再追求更强实时性
5. speech 的正式结果应收敛到统一多模态契约，不再单独造字段体系

---

## 11. 最终结论

当前系统最适合的语音接入思路不是推翻现代码重做，而是：

- 承认当前已经存在的 `multimodal-service -> consultation-service` 两段式链路
- 承认当前已经存在的 `capture -> inference -> live -> bundle` 四层多模态结构
- 在这套结构上把语音模态的数据契约、状态边界、联调顺序和验收标准补齐

如果一句话概括这份代码对齐版方案，就是：

**speech 继续作为当前最成熟的主链模态，结果沉淀到统一多模态结构里，业务真相继续落在 consultation turn，前端展示读 live，单轮复盘读 bundle。**
