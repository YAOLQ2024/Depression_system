# 语音情绪识别接入系统的完整设计与实现方案

## 1. 文档目标

本文档只聚焦一个模态：

- `语音情绪识别`

目标是先把这一条链路完整跑通，再考虑文本、面部、姿态和 EEG。这里的“跑通”指：

1. 前端可以采集一轮回答音频并上传
2. 后端可以调用语音情绪模型完成推理
3. 结果可以稳定存储
4. 结果可以回写到问诊链路
5. 结果可以稳定显示在问诊页右侧看板

本文故意不讨论：

- EEG
- ASR 模型部署细节
- 多模态总线的一次性全量设计

---

## 2. 当前建议的设计原则

为了尽快走通系统，不采用“全模态一次到位”的重方案，而采用：

- `一轮回答（turn）对应一个语音情绪识别结果`
- `录音结束后识别一次`
- `识别完成后立刻存库`
- `识别完成后立刻刷新看板`

不采用：

- 录音过程中每几秒切片做一次语音情绪识别
- 语音模态先做实时流式情绪曲线

原因很简单：

1. 一轮一结果更稳定，更适合问诊语境
2. 更容易解释、更容易写论文
3. 更容易保证数据库与看板一致
4. 更适合先做 MVP

---

## 3. 核心概念

### 3.1 session

`consultation session` 表示一次完整问诊。

例如：

- 患者登录
- 进入数字人问诊
- 从第一题做到最后一题

这整段过程是一个 `session`。

### 3.2 turn

`turn` 表示一轮问答。

例如：

- 数字人问一个问题
- 患者回答一次

这就是一个 `turn`。

### 3.3 语音情绪结果

当前方案里：

- 一个 `turn`
- 对应一条 `speech emotion result`

也就是说，系统不保存“这一轮里面很多片段的很多语音情绪结果”，而只保存“这一轮最终的一个语音情绪识别结论”。

---

## 4. 最小表设计

先只保留三层：

```text
consultation_sessions
    1
    |
    | 1:N
    v
consultation_turns
    1
    |
    | 1:1
    v
speech_emotion_results
```

其中音频文件本体存对象存储，不直接放数据库。

### 4.1 `consultation_sessions`

保留现有主表，不需要因为语音情绪识别重做。

建议只依赖已有主键：

- `id`
- `user_id`
- `status`
- `current_stage_id`
- `created_at`
- `updated_at`

### 4.2 `consultation_turns`

保留现有 turn 表，继续作为“本轮回答主表”。

语音模态至少依赖这些字段：

- `id`
- `session_id`
- `question_key`
- `stage_id`
- `node_id`
- `input_type`
- `raw_input`
- `transcript_text`
- `original_audio_uri`
- `normalized_wav_uri`
- `response_started_at`
- `response_completed_at`
- `created_at`

### 4.3 `speech_emotion_results`

新增一张专门表，专门存“本轮回答的语音情绪识别结果”。

建议字段：

```text
speech_emotion_results
- id
- consultation_turn_id
- consultation_session_id
- model_name
- model_version
- primary_label
- primary_score
- top3_payload
- inference_status
- error_message
- created_at
- updated_at
```

字段解释：

- `consultation_turn_id`
  这条结果属于哪一轮回答
- `consultation_session_id`
  冗余保存一次，便于查询与统计
- `model_name`
  如 `audio_emotion`
- `model_version`
  用于复现、验收、论文说明
- `primary_label`
  主情绪标签
- `primary_score`
  主标签置信度
- `top3_payload`
  Top-3 情绪分布 JSON
- `inference_status`
  `processing / completed / failed`
- `error_message`
  失败原因

---

## 5. 音频文件存储设计

### 5.1 存什么

音频文件本体不存数据库，存对象存储（MinIO）。

这一阶段建议保留两份音频对象：

- `original_audio_uri`
  - 浏览器原始上传音频
  - 用于留档、审计、回放、追溯
- `normalized_wav_uri`
  - `multimodal-service` 统一转好的 `16k / mono / wav`
  - 用于 Dolphin ASR 和语音情绪识别的标准输入

数据库里只保存：

- `original_audio_uri`
- `normalized_wav_uri`
- `storage_provider`
- `storage_object_key`
- `mime_type`
- `file_size_bytes`
- `duration_ms`

### 5.2 为什么这样做

因为：

1. 原始音频需要作为留档真相源
2. 标准化 wav 需要作为模型统一输入源
3. 以后可能需要人工复核与重跑模型
4. 数据库存元数据更轻

---

## 6. 接口设计

本阶段的正式链路由 `consultation-service` 对前端暴露主入口，再由它调用 `multimodal-service`。

### 6.1 提交一轮语音回答并完成识别

```http
POST /api/v1/consultations/{session_id}/turns/audio
```

请求内容建议包含：

- `question_key`
- `stage_id`
- `node_id`
- `audio_file`
- `response_started_at`
- `response_completed_at`

接口职责：

1. 校验 session 与权限
2. 把浏览器原始音频上传到对象存储
3. 创建 `consultation_turn`
4. 调用 `multimodal-service`
5. `multimodal-service` 将原始音频转成标准 wav
6. `multimodal-service` 保存 `normalized_wav_uri`
7. `multimodal-service` 基于同一份 wav 异步并行执行：
   - Dolphin ASR
   - 语音情绪识别
8. `multimodal-service` 返回：
   - `transcript_text`
   - `normalized_wav_uri`
   - `speech_emotion_result`
9. `consultation-service` 回写：
   - `consultation_turns.transcript_text`
   - `consultation_turns.normalized_wav_uri`
   - `speech_emotion_results`
10. 返回 turn 和语音情绪结果

返回建议：

```json
{
  "consultation_turn": {},
  "speech_emotion_result": {}
}
```

### 6.2 查询某一轮语音情绪结果

```http
GET /api/v1/consultations/{session_id}/turns/{turn_id}
```

返回建议：

```json
{
  "consultation_turn": {},
  "speech_emotion_result": {}
}
```

这条接口用于：

- 页面刷新后恢复状态
- 看板重载
- 调试与验收

---

## 7. 端到端流程

### 7.1 输入

前端问诊页：

1. 用户点击开始录音
2. 浏览器采集麦克风
3. 用户结束录音
4. 前端将音频上传给后端

### 7.2 后端接收

`consultation-service` 作为问诊主链入口接收请求。

### 7.3 后端处理

处理链路建议分两层：

#### consultation-service 负责：

1. 接收浏览器原始音频
2. 上传原始音频到 MinIO，得到 `original_audio_uri`
3. 创建 `consultation_turn`
4. 把 `original_audio_uri` 和本轮上下文传给 `multimodal-service`

#### multimodal-service 负责：

1. 从原始音频生成标准 `16k / mono / wav`
2. 保存标准 wav，得到 `normalized_wav_uri`
3. 基于同一份 wav 异步并行执行：
   - Dolphin ASR
   - 语音情绪识别
4. 返回：
   - `transcript_text`
   - `normalized_wav_uri`
   - `speech_emotion_result`

#### consultation-service 再回写：

1. `consultation_turns.transcript_text`
2. `consultation_turns.normalized_wav_uri`
3. `speech_emotion_results`
4. 把最终结果返回前端

### 7.4 前端显示

前端收到成功响应后，立即刷新右侧看板。

第一阶段看板只显示一项核心结果：

- 主情绪标签

例如：

- 语音情绪：悲伤

这里故意不要求第一阶段看板展示：

- 置信度
- Top-3

原因是：

1. 先把“这轮回答最终是什么情绪”稳定显示出来
2. 先降低前端展示复杂度
3. 避免第一阶段把模型原始信息过多暴露到看板 UI
4. 让存储与展示先解耦，后面如需扩展再加

这里要特别说明：

- `主情绪标签`
- `主标签置信度`
- `Top-3 排名`

这三项都可以直接从当前语音情绪识别模型得到，属于模型真实输出，不是前端二次猜测出来的。

当前原始模型实际输出的是：

- `label`
- `score`
- `extra.topk`

因此本方案里：

- `primary_label` 对应模型的 `label`
- `primary_score` 对应模型的 `score`
- `top3_payload` 对应模型的 `extra.topk`

但第一阶段看板只读取并展示：

- `primary_label`

---

## 8. 结果形态对照

为了避免后面联调时混淆，这里把“模型原始输出 / 看板显示 / 数据库存储”三层结果明确写出来。

### 8.1 模型原始输出长什么样

当前语音情绪识别模型原始输出的核心结构是：

```json
{
  "modality": "audio",
  "label": "sad",
  "score": 0.82,
  "extra": {
    "topk": [
      ["sad", 0.82],
      ["neutral", 0.11],
      ["fear", 0.04],
      ["happy", 0.02]
    ]
  },
  "timestamp": "2026-05-19 14:30:05"
}
```

这里每个字段的含义是：

- `label`
  模型最终判定的主情绪标签
- `score`
  主标签对应的概率或置信分数
- `extra.topk`
  模型输出的排序结果列表
- `timestamp`
  模型返回时间

注意：

- 这是模型直接输出
- 这一步还不是前端看板最终显示格式
- 这一步也还不是数据库最终落库格式

### 8.2 看板中看到的是什么样

右侧看板应该显示成用户可理解的样子，而不是原始 JSON。

建议展示形态：

```text
语音情绪：悲伤
状态：已完成
```

也就是说，看板显示层会做两件事：

1. 字段重命名
   - `label` -> `语音情绪`
   - `inference_status` -> `状态`

2. 状态语义化
   - `completed` -> `已完成`
   - `processing` -> `分析中`
   - `failed` -> `分析失败`

注意：

- 第一阶段看板只显示主情绪标签
- `score` 和 `topk` 仍然保留在后端返回与数据库中
- 它们主要用于后续验收、调试、统计和二阶段扩展

### 8.3 数据库存到的是什么样

数据库不建议把模型原始返回原封不动塞进去，而应该存成系统自己的标准结果结构。

如果按本文的最小表设计，`speech_emotion_results` 一条记录建议存成：

```json
{
  "id": "ser_001",
  "consultation_turn_id": "turn_001",
  "consultation_session_id": "cs_001",
  "model_name": "audio_emotion",
  "model_version": "v1",
  "primary_label": "sad",
  "primary_score": 0.82,
  "top3_payload": [
    { "label": "sad", "score": 0.82 },
    { "label": "neutral", "score": 0.11 },
    { "label": "fear", "score": 0.04 }
  ],
  "inference_status": "completed",
  "error_message": null,
  "created_at": "2026-05-19T14:30:06+08:00",
  "updated_at": "2026-05-19T14:30:06+08:00"
}
```

### 8.4 三层之间怎么对应

可以直接按这张表理解：

| 层级 | 目的 | 核心字段 |
| --- | --- | --- |
| 模型原始输出 | 模型自身推理结果 | `label` `score` `extra.topk` |
| 看板展示 | 给用户/医生看 | 主情绪标签、状态 |
| 数据库存储 | 给系统持久化 | `primary_label` `primary_score` `top3_payload` `inference_status` |

最关键的映射关系是：

- 模型 `label` -> 数据库 `primary_label` -> 看板“语音情绪”
- 模型 `score` -> 数据库 `primary_score`
- 模型 `extra.topk` -> 数据库 `top3_payload`
- 数据库 `inference_status` -> 看板“状态”

### 8.5 为什么要分这三层

因为这三层职责不同：

1. 模型输出层
   只关心推理本身

2. 数据库存储层
   关心长期保存、查询、统计、复现

3. 看板展示层
   关心用户可读、简洁、稳定

如果不把这三层区分开，后面很容易出现：

- 前端直接绑死模型原始字段
- 数据库保存过于随意
- 看板和落库字段对不上

---

## 9. 看板刷新逻辑

这里的“看板”特指问诊页右侧实时结果侧栏。

### 9.1 当前阶段推荐逻辑

语音模态不要做几秒一刷新，而采用：

- 一轮回答结束
- 接口返回识别结果
- 前端立即更新看板

第一阶段看板只更新两项：

- 主情绪标签
- 当前状态

不在第一阶段看板中展示：

- 置信度
- Top-3

### 9.2 显示状态

看板至少有三种状态：

1. `pending`
   - 等待用户开始录音
2. `processing`
   - 已录完，正在分析
3. `completed`
   - 已生成语音情绪结果

失败则显示：

4. `failed`
   - 分析失败，请重试

### 9.3 为什么不用“边录边刷”

因为语音模态与 face / pose 不一样：

- face / pose 适合高频采样
- 语音情绪更适合基于整轮回答做稳定判断

---

## 9. 如何避免数据库与看板不一致

这是本设计里必须注意的点。

### 9.1 不推荐的做法

不推荐：

- 前端上传音频后立即高频轮询猜结果
- 后端一边写库，一边让前端无状态乱刷新

这样容易出现：

- 前端读到半成品
- 看板显示空值
- 数据库和 UI 不一致

### 9.2 推荐的做法

推荐：

- 后端先完成写库和识别
- 接口再统一返回当前最终结果
- 前端根据返回结果更新看板

也就是说：

**先完成写数据库，再更新看板。**

这样逻辑是串行一致的，不容易出错。

---

## 10. 时序图

下面是一版针对“语音情绪识别单模态”的最小时序图。

```text
患者/浏览器
    |
    | 1. 开始录音
    | 2. 结束录音，得到一整段音频
    v
consultation 前端
    |
    | 3. POST /consultations/{session_id}/turns/audio
    |    - audio_file
    |    - question_key
    |    - stage_id
    |    - node_id
    |    - response_started_at
    |    - response_completed_at
    v
consultation-service
    |
    | 4. 上传原始音频到 MinIO
    |    -> original_audio_uri
    | 5. 创建 consultation_turn
    | 6. 调用 multimodal-service
    |    - original_audio_uri
    |    - 本轮上下文
    v
multimodal-service
    |
    | 7. 生成标准 wav
    |    -> normalized_wav_uri
    | 8. 基于同一份 wav 异步并行执行
    |    ├─ Dolphin ASR
    |    └─ 语音情绪识别
    | 9. 汇总返回
    |    - transcript_text
    |    - normalized_wav_uri
    |    - label
    |    - score
    |    - topk
    v
consultation-service
    |
    | 10. 回写 consultation_turn.transcript_text
    | 11. 回写 consultation_turn.normalized_wav_uri
    | 12. 写入/更新 speech_emotion_result
    | 13. 组装响应
    v
consultation 前端
    |
    | 14. 更新右侧看板
    |     - 主情绪标签
    |     - 状态
    v
患者看到结果
```

如果用更简短的“状态流”表示，就是：

```text
录音中
  -> 上传原始音频
  -> 原始音频已留档
  -> wav 生成中
  -> ASR/情绪并行处理中
  -> 结果已回写
  -> 看板刷新完成
```

这版时序图对应的是当前第一阶段最稳的实现方式：

- 一轮回答
- 一次标准化
- 一次并行推理
- 一次统一回写
- 一次看板刷新

而不是“录音过程中不断切片识别、不断推送看板”。

---

## 11. 与当前系统的关系

本方案是一个“最小闭环方案”，不是一次性推翻当前系统。

它可以作为当前系统的简化落地路径：

- 问诊主流程仍由 `consultation-service` 控制
- 语音情绪模型仍然可以部署在 `multimodal-service` 或内部推理模块中
- 但业务对象先收敛到最小：
  - `consultation_sessions`
  - `consultation_turns`
  - `speech_emotion_results`

等这一条跑通后，再把：

- 文本情绪
- 面部情绪
- 姿态情绪

按同样的思路逐步接入。

---

## 12. 最小实施步骤

建议严格按下面顺序实施，不要同时平推前后端。

### Step 1：先确认模型输入输出契约

先把语音情绪模型当前真实能力固定下来：

- 输入：一整段回答音频
- 输出：
  - `label`
  - `score`
  - `extra.topk`

这一阶段先明确三条约束：

1. 不做流式语音情绪识别
2. 不做按 3 秒或 5 秒切片的多结果返回
3. 一轮回答只返回一个最终语音情绪结果

交付物建议：

- 在文档中固定模型输出示例
- 在代码中固定一个统一的内部结果结构

### Step 2：确定服务职责归属

先把职责边界定死：

- `consultation-service`
  - 负责问诊 turn 业务语义
  - 负责保存原始音频
  - 负责创建 `consultation_turn`
  - 负责回写最终文本和情绪结果
- `multimodal-service`
  - 负责音频标准化
  - 负责生成 `normalized_wav_uri`
  - 负责 Dolphin ASR
  - 负责语音情绪识别
- `MinIO`
  - 负责原始音频与标准 wav 的对象存储

这一步的关键不是写代码，而是避免后面出现：

- 原始音频和标准 wav 谁来保存
- 标准化过程放在哪个服务
- 最终 transcript_text 到底由谁生成

### Step 3：新增 `speech_emotion_results` 表

在 `consultation-service` 对应数据库里新增：

- `speech_emotion_results`

字段建议至少包括：

- `id`
- `consultation_turn_id`
- `consultation_session_id`
- `model_name`
- `model_version`
- `primary_label`
- `primary_score`
- `top3_payload`
- `inference_status`
- `error_message`
- `created_at`
- `updated_at`

这一步要完成的事情：

1. 写 ORM 模型
2. 写 Alembic 迁移
3. 确保 `consultation_turn_id` 建立唯一约束或唯一索引
   - 因为当前方案是一轮回答只对应一条语音情绪结果
4. 本地或容器里执行迁移

### Step 4：确定音频对象存储路径规则

不要先随便上传文件，先定命名规则。

建议至少明确两套对象路径：

```text
consultation-audio/{session_id}/{turn_id}/original/{filename}
consultation-audio/{session_id}/{turn_id}/normalized/response.wav
```

数据库建议同时保存：

- `original_audio_uri`
- `normalized_wav_uri`

这一步的目标是让以后：

- 人工复核能找到原始音频
- 模型重跑能找到标准 wav
- 问题排查时能区分“留档源”和“模型输入源”

### Step 5：在后端增加“提交一轮语音回答”接口

新增接口：

```http
POST /api/v1/consultations/{session_id}/turns/audio
```

建议实现顺序如下：

1. 校验登录身份
2. 校验 `session_id` 是否存在
3. 校验当前问诊是否允许提交这一轮回答
4. 接收原始音频文件与业务字段
5. 上传原始音频到 MinIO，得到 `original_audio_uri`
6. 创建 `consultation_turn`
7. 调用 `multimodal-service`
8. 接收 `multimodal-service` 返回的：
   - `transcript_text`
   - `normalized_wav_uri`
   - `speech_emotion_result`
9. 回写 `consultation_turn`
10. 写入/更新 `speech_emotion_results`
11. 返回 `consultation_turn + speech_emotion_result`

这里要注意：

- 对前端来说，这条接口仍然建议先同步返回最终结果
- 也就是前端等这一轮回答处理完成后再刷新看板
- 但 `multimodal-service` 内部可以在标准 wav 生成之后并行跑 ASR 和情绪识别

### Step 6：实现 `multimodal-service` 的标准化与并行推理

`multimodal-service` 内部建议按下面顺序实现：

1. 根据 `original_audio_uri` 读取原始音频
2. 生成标准 `16k / mono / wav`
3. 上传标准 wav 到 MinIO，得到 `normalized_wav_uri`
4. 基于同一份 wav 异步并行执行：
   - Dolphin ASR
   - 语音情绪识别
5. 等两边完成后汇总统一响应

这一阶段要求：

- ASR 和情绪识别必须吃同一份标准 wav
- 不允许 ASR 吃原始音频、情绪模型吃 wav 的双输入源分裂
- 如果任一分支失败，响应里必须明确失败字段

### Step 7：后端固定状态流转

语音情绪识别结果至少要有三态：

- `processing`
- `completed`
- `failed`

推荐流转：

1. 创建结果记录时：
   - `processing`
2. 模型识别成功后：
   - `completed`
3. 模型识别失败后：
   - `failed`

失败时必须写：

- `error_message`

这样前端和后续排障时就不会只看到“没有结果”，而是能知道：

- 还在处理中
- 还是已经失败

### Step 8：把模型原始输出映射成系统结果结构

模型原始返回：

- `label`
- `score`
- `extra.topk`

系统内部结果结构建议统一成：

- `primary_label`
- `primary_score`
- `top3_payload`

映射关系固定为：

- `label -> primary_label`
- `score -> primary_score`
- `extra.topk -> top3_payload`

这里要做的不是简单转字段名，而是把系统内部契约稳定下来。以后即便模型内部换了，只要仍然能映射到这三个字段，前后端就不用一起改。

### Step 9：回写 `consultation_turns` 的正式文本与 wav URI

`consultation-service` 在收到 `multimodal-service` 返回后，必须统一回写：

- `consultation_turns.transcript_text`
- `consultation_turns.normalized_wav_uri`
- `speech_emotion_results`

这里的关键约束是：

- 最终正式 `transcript_text` 只认 Dolphin ASR 返回值
- 浏览器实时字幕或预览文本不作为正式落库真相源
- `normalized_wav_uri` 必须与本轮情绪识别使用的 wav 对应

### Step 10：前端录音提交链路改成“提交后等最终结果”

前端这一阶段不要这样做：

- 一上传就开始高频轮询
- 一边等后端，一边自己猜测结果状态

而要这样做：

1. 用户完成录音
2. 前端提交整段音频
3. 前端把语音看板状态切成 `processing`
4. 等待接口返回
5. 返回成功后，用响应里的结果直接更新看板
6. 返回失败后，把看板切成 `failed`

这一步的重点是：

- 看板更新由接口响应驱动
- 不是由前端盲轮询驱动

### Step 11：第一阶段看板只显示主情绪标签

右侧看板中的语音区域，第一阶段只做：

- 状态
- 主情绪标签

建议显示逻辑：

- `pending`：等待语音提交
- `processing`：语音分析中
- `completed`：显示主情绪标签
- `failed`：显示分析失败

这一步不要先把：

- `置信度`
- `Top-3`

做进看板主展示。它们先作为后端返回和数据库存储字段保留即可。

### Step 12：增加查询接口用于页面恢复

新增接口：

```http
GET /api/v1/consultations/{session_id}/turns/{turn_id}
```

主要用于：

- 页面刷新后恢复当前轮次的语音情绪结果
- 调试时检查这轮结果是否已写入
- 后续验收时做接口回看

这一步很重要，因为没有查询接口的话，页面一刷新就只能靠前端内存状态，难以验证完整闭环。

### Step 13：补齐联调与验收检查项

至少按下面顺序逐项验证：

1. 浏览器能正常录音
2. 音频能成功上传到后端
3. MinIO 中能看到原始音频对象
4. `consultation_turns` 成功新增一条记录
5. `multimodal-service` 成功生成标准 wav
6. MinIO 中能看到标准 wav 对象
7. Dolphin ASR 返回正式 `transcript_text`
8. 语音情绪模型返回 `label / score / topk`
9. `consultation_turns` 回写 `transcript_text`
10. `consultation_turns` 回写 `normalized_wav_uri`
11. `speech_emotion_results` 更新为 `completed`
12. 前端收到最终结果
13. 看板显示主情绪标签
14. 刷新页面后仍能通过查询接口恢复显示

### Step 14：确认第一阶段完成边界

第一阶段完成的判断标准应该明确写出来：

- 能上传一整段回答音频
- 能把原始音频存到 MinIO
- 能把标准 wav 存到 MinIO
- 能基于标准 wav 完成一次 Dolphin ASR
- 能基于标准 wav 完成一次语音情绪识别
- 能把文本和情绪结果入库
- 能在看板上显示主情绪标签
- 页面刷新后结果不丢

第一阶段明确不做：

- 录音过程中的实时语音情绪流
- 多段切片结果展示
- 置信度和 Top-3 的复杂看板展示
- 与 face / pose / text 的多模态融合展示

---

## 13. 最终结论

当前阶段最适合先落地的，不是“完整多模态总线”，而是：

**先把语音情绪识别这一条做成最小、稳定、可解释、可展示的完整闭环。**

这条闭环的核心原则是：

- 一轮回答对应一个结果
- 原始音频与标准 wav 分层存储
- Dolphin ASR 和语音情绪识别共用同一份标准 wav
- ASR 与情绪识别在 `multimodal-service` 内部异步并行
- `consultation-service` 统一回写正式文本与情绪结果
- 接口完成后再刷新看板
- 先保证一致性，再考虑实时化

这会让系统更容易开发、更容易调试，也更容易用于论文和项目验收展示。
