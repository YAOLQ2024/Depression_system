# 四模态接入总计划（Speech / Text / Face / Pose）

更新时间：2026-05-21

适用仓库：`depression-system`

适用范围：`consultation` 患者端正式问诊阶段的四模态接入、存储、读取、页面展示与后续总方案编写

---

## 1. 文档目标

这份文档不是单讲某个模态，而是给后续 4 模态总方案提供统一骨架。

覆盖范围：

- `speech`
- `text`
- `face`
- `pose`

本文档重点解决三件事：

1. 明确四模态在当前代码中的共同结构
2. 明确 `live / bundle / turn / capture` 的关系
3. 明确下一步 4 模态总接入方案应如何分阶段推进

---

## 2. 先说结论

当前仓库已经不是“4 模态都待设计”的状态，而是已经有一个可工作的统一多模态骨架：

- `consultation-session`
- `multimodal-session`
- `capture`
- `inference result`
- `live`
- `turn bundle`

因此后续 4 模态总方案不应该从“是否要做统一总线”开始讨论，而应该从：

- 如何补齐各模态缺口
- 如何让字段契约完全一致
- 如何让前端只读统一视图

开始推进。

---

## 3. 统一术语

### 3.1 consultation session

表示一次完整问诊业务会话。

它是问诊主状态机的业务主轴。

### 3.2 multimodal session

表示与某次问诊会话绑定的多模态处理会话。

它是 4 模态统一处理与聚合的技术主轴。

### 3.3 turn

表示一轮问答。

例如：

- 数字人问一个问题
- 用户回答一次

### 3.4 capture

表示原始采样或原始输入事件。

典型例子：

- 一段音频上传
- 一帧 face 图像
- 一帧 pose 图像

### 3.5 inference result

表示单次模型输出后的标准化结果。

典型例子：

- 一次语音情绪输出
- 一次文本情绪输出
- 一次表情帧输出
- 一次姿态帧输出

### 3.6 live

表示当前会话最新可展示状态。

它是 session 级、覆盖式快照。

### 3.7 bundle

表示某一轮 turn 的聚合特征包。

它是 turn 级、可回溯快照。

---

## 4. `live / bundle / turn / capture` 关系图

这是后续写总方案时最需要反复引用的关系图。

```text
consultation_session
    |
    | 1:1
    v
multimodal_session
    |
    | 1:N
    v
captures
    |
    | 1:N
    v
inference_results
    |
    | 聚合为 session 级最新态
    +-------------------------------> live
    |
    | 按 turn_id 聚合
    v
turn_bundle
    ^
    |
    | 1:1 or 1:N read relationship
consultation_turn
```

也可以从“读写视角”理解：

```text
写路径：
capture -> inference_result -> live / turn_bundle

业务路径：
consultation_turn <-> turn_bundle

展示路径：
front-end panel -> live

复盘/验收路径：
front-end or downstream -> turn_bundle
```

---

## 5. 四个对象分别负责什么

### 5.1 capture

`capture` 负责记录“原始采样事件”。

主要特点：

- 粒度最细
- 和设备/原始输入最接近
- 可用于调试、追溯、质量判定

典型字段：

- `session_id`
- `turn_id`
- `question_key`
- `modality`
- `sample_index`
- `sample_started_at`
- `sample_ended_at`
- `capture_payload`

当前最典型的使用场景：

- `audio`：一段回答音频
- `face`：一帧图像
- `pose`：一帧图像

### 5.2 turn

`turn` 负责记录“业务上这一轮问答的正式真相”。

它不应该承载全部模型细节。

它更关心：

- 这轮是谁答的
- 这轮答的是哪一题
- 正式文本是什么
- 正式音频引用是什么
- 问诊流程如何推进

### 5.3 live

`live` 负责让前端知道“此刻最新结果是什么”。

它不是历史表，而是最新态缓存。

特点：

- session 级
- 会被新结果覆盖
- 给右侧看板

### 5.4 bundle

`bundle` 负责让系统知道“某一轮最终结果是什么”。

它不是每一帧，也不是最新快照，而是 turn 级汇总产物。

特点：

- turn 级
- 聚合后的稳定结果
- 适合回写、复盘、验收、风控消费

---

## 6. 四模态在当前系统中的共同模式

### 6.1 speech

模式：

- 原始输入是音频
- 先做 ASR
- 再得到 `speech emotion`
- 同时产出 `text emotion`

更像“主链模态 + 副链文本来源”。

### 6.2 text

模式：

- 原始输入是正式文本
- 可来自 `speech transcript`
- 也可来自 `manual_input`

更像“语义模态”。

### 6.3 face

模式：

- 连续帧输入
- 每帧可推理
- turn 结束后聚合

更像“高频视觉模态”。

### 6.4 pose

模式：

- 连续帧输入
- 单帧可能处于 collecting
- turn 结束后聚合统计更重要

更像“窗口型视觉模态”。

---

## 7. 当前推荐的读写分层

### 7.1 浏览器写入

浏览器只负责提交原始输入：

- 音频
- face 帧
- pose 帧
- 手工文本

### 7.2 `multimodal-service` 写入

`multimodal-service` 负责：

- capture 记录
- inference result 记录
- live 更新
- bundle 更新

### 7.3 `consultation-service` 写入

`consultation-service` 负责：

- 业务 turn 真相
- `consultation_turn.turn_summary_payload` 缓存
- `consultation_session.multimodal_live_payload` 缓存

### 7.4 前端读取

前端统一读取：

- `consultations/{session_id}/multimodal/live`
- `consultations/{session_id}/turns/{turn_id}/multimodal/bundle`

不自己拼底层 capture 和 inference 明细。

---

## 8. 当前统一契约建议

### 8.1 live 契约

统一包含：

- `speech`
- `text`
- `face`
- `pose`
- `updated_at`

其中：

- `speech/text` 偏向“单次结果”
- `face/pose` 偏向“最近采样结果”

### 8.2 bundle 契约

统一包含：

- `speech_features`
- `text_features`
- `face_features`
- `pose_features`

其中：

- `speech/text` 通常是一轮一条稳定结果
- `face/pose` 是多帧聚合结果

### 8.3 turn 契约

统一包含业务真相字段：

- `input_type`
- `raw_input`
- `audio_uri`
- `transcript_text`
- `transcript_source`
- `response_started_at`
- `response_completed_at`

### 8.4 capture 契约

统一包含：

- `session_id`
- `turn_id`
- `question_key`
- `modality`
- `sample_index`
- `sample_started_at`
- `sample_ended_at`
- `capture_payload`

---

## 9. 当前系统最关键的 4 个接入缺口

### 9.1 手工文本输入还没真正纳入文本模态

现状：

- `manual_input` 会进入 `consultation_turn`
- 但还没稳定进入 `multimodal-service` 的 `text emotion` 链路

影响：

- 同样是正式回答，语音和手输的文本模态能力不一致

### 9.2 face / pose 原始帧未形成稳定留档策略

现状：

- 当前更多是元数据与推理结果入库
- 对象存储层面还不够明确

影响：

- 后续复盘和训练回看能力不足

### 9.3 live 与 bundle 的字段粒度尚未完全对齐

现状：

- `face/pose` 在 live 中更像最近态
- 在 bundle 中更像汇总态

问题不在于不同，而在于文档还没有把这种差异讲透。

### 9.4 前端对 bundle 的消费还比较弱

现状：

- `live` 已有明确看板消费路径
- `bundle` 已有接口
- 但 UI 还没有把每轮复盘能力真正做出来

---

## 10. 四模态总接入的实施顺序

### Phase 1：先统一契约

目标：

- 固定 `live / bundle / turn / capture` 的关系
- 固定 4 模态的统一命名

交付物：

- 文档定稿
- 前端类型统一
- 后端 schema 统一

### Phase 2：补齐 speech + text

目标：

- 把最成熟的语义链路彻底稳定下来

重点：

- 语音转写
- 语音情绪
- 文本情绪
- `manual_input` 文本情绪补齐

### Phase 3：补齐 face + pose

目标：

- 让视觉模态稳定进入 capture -> inference -> bundle

重点：

- 采样节奏
- 质量标记
- turn 窗口聚合

### Phase 4：前端统一读 live / bundle

目标：

- 看板只看 `live`
- 复盘只看 `bundle`
- 清掉假数据与旧 prototype 类型

### Phase 5：为 4 模态融合预留接口

目标：

- 不在当前阶段直接做风险结论融合
- 但要让后续 `risk-service` 能稳定消费标准化 bundle

---

## 11. 后续总方案写作建议

你后面如果要写“4 模态接入总方案”，最建议按下面 5 个章节展开：

1. 统一对象模型
   - `session / turn / capture / live / bundle`

2. 四模态分别接入
   - `speech`
   - `text`
   - `face`
   - `pose`

3. 统一接口层
   - 浏览器入口
   - consultation-service 业务读口
   - multimodal-service 模态写口与聚合读口

4. 统一存储层
   - 业务真相
   - 原始采样
   - 推理结果
   - 聚合结果

5. 验收与演进路线
   - 单模态验收
   - 四模态联调
   - 风险融合

---

## 12. 最终结论

当前最重要的不是继续争论“是不是要做统一多模态架构”，因为现代码里它已经存在雏形。

当前最重要的是把这个雏形讲清楚并补齐：

- `capture` 负责原始采样
- `turn` 负责业务真相
- `live` 负责当前展示
- `bundle` 负责每轮固化

一句话总结：

**后续 4 模态总方案应建立在“turn 是业务主轴，capture 是采样明细，live 是会话最新态，bundle 是轮次聚合态”这四层关系之上。**
