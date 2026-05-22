# 文本情绪识别接入系统的代码对齐版实施方案

更新时间：2026-05-21

适用仓库：`depression-system`

适用范围：`consultation` 患者端数字人问诊阶段的文本情绪识别接入、存储、展示与接口编排

---

## 1. 文档目标

本文档只聚焦一个模态：

- `text`

但这里的文本模态有明确边界：

- 仅服务于 `数字人问诊阶段`
- 文本来源仅限 `语音转写 transcript`
- 不覆盖 `manual_input`
- 不覆盖后续 `量表问诊`

因此本文档的目标不是设计“全输入源统一文本情绪系统”，而是把当前已经存在的：

- `speech -> transcript -> text emotion`

这条副链，整理成一版代码对齐、可交付、可验收的正式方案。

---

## 2. 先说结论

在当前业务边界下，文本情绪识别其实已经基本走通。

这里的“走通”指的是：

1. 数字人问诊阶段用户回答语音
2. 前端把音频上传到 `multimodal-service`
3. `multimodal-service` 完成 ASR
4. 用正式 transcript 触发文本情绪识别
5. 文本结果进入 `live.text`
6. 文本结果进入 `turn_bundle.text_features`
7. 前端可以统一展示文本模态结果

因此当前文本模态的重点，不是“补齐 manual_input”，而是：

- 明确业务边界
- 固定文本结果契约
- 固定它在 `live / bundle / turn` 中的位置

---

## 3. 当前业务范围定义

### 3.1 纳入范围

当前文本情绪识别只纳入下面这条链路：

- 数字人问诊阶段
- 用户用语音回答
- Dolphin ASR 生成正式 `transcript_text`
- 基于该 transcript 做 `text emotion`

### 3.2 明确不纳入范围

以下场景当前不属于文本情绪识别范围：

- `manual_input`
- 后续量表问诊填写文本
- 浏览器中间态字幕草稿
- 临时输入框草稿文本

### 3.3 业务真相边界

文本情绪识别只认一个正式文本真相源：

- `Dolphin ASR` 产生的最终 transcript

因此文本模态当前不需要处理“多个文本入口统一归并”的问题。

---

## 4. 当前代码现实

从当前实现看，文本模态已经是 `multimodal-service` 的正式模态之一。

它当前的真实位置是：

- 它不是浏览器单独上传的一条主链
- 它是 `audio-turn` 内部在 ASR 完成后的副链结果

也就是说：

```text
audio upload
  -> ASR transcript
  -> text emotion inference
  -> live.text
  -> turn_bundle.text_features
```

因此文本模态当前和语音模态的关系应理解为：

- `speech` 是主输入模态
- `text` 是语义副链模态

---

## 5. 当前推荐的职责划分

### 5.1 `consultation-service`

负责：

- 保存正式业务 `turn`
- 保存最终 `transcript_text`
- 保存 `transcript_source`
- 保证问诊状态机推进

不负责：

- 文本情绪模型推理
- 文本 `live` 聚合
- 文本 `bundle` 聚合

### 5.2 `multimodal-service`

负责：

- ASR 完成后的文本情绪推理
- 文本 inference result 持久化
- 更新 `live.text`
- 更新 `turn_bundle.text_features`

### 5.3 前端

负责：

- 展示 `live.text`
- 在需要时读取某一轮 `turn bundle`

不负责：

- 自己拼文本情绪
- 对文本做前端关键词猜测

---

## 6. 当前数据归属

### 6.1 `consultation_turns`

保存业务真相文本：

- `transcript_text`
- `transcript_source`

当前文本模态仍然应围绕这份正式 transcript 工作。

### 6.2 `multimodal_inference_results`

保存一次文本情绪推理的标准化结果。

### 6.3 `live.text`

保存会话级最新文本模态快照，用于右侧状态看板。

### 6.4 `turn_bundle.text_features`

保存某一轮 turn 的正式文本模态结果，用于：

- 页面刷新恢复
- 单轮复盘
- 后续多模态消费

---

## 7. 文本模态统一输出契约

### 7.1 系统内部标准结果

当前文本模态建议统一为如下结构：

```json
{
  "modality": "text",
  "status": "ready",
  "primary_label": "neutral",
  "primary_score": 0.79,
  "top_3_labels": [
    { "label": "neutral", "score": 0.79 },
    { "label": "sad", "score": 0.14 },
    { "label": "anxiety", "score": 0.04 }
  ],
  "negative_terms": ["失眠", "睡不着"],
  "transcript_text": "最近一直睡不好，很累。",
  "captured_at": "2026-05-21T14:30:05+08:00"
}
```

### 7.2 当前必须固定的字段

建议至少固定以下字段：

- `status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `negative_terms`
- `transcript_text`
- `captured_at`

### 7.3 不需要额外暴露的来源差异

由于当前文本只来自语音转写，因此对前端不需要再区分：

- `text_source = dolphin_final`
- 其他文本来源

内部可保留，但不需要把“多来源统一设计”写成当前阶段目标。

---

## 8. 当前推荐接口理解方式

### 8.1 不新增独立文本主入口

当前业务范围下，不建议新增浏览器单独调用的文本情绪接口。

更合理的方式是继续沿用：

1. 浏览器上传音频到 `audio-turns`
2. `multimodal-service` 完成 ASR
3. 直接在内部触发文本情绪推理
4. 更新 `live.text`
5. 更新 `turn_bundle.text_features`

### 8.2 前端读取

前端继续统一读取：

```http
GET /api/v1/multimodal/sessions/{session_id}/live
```

读取文本最新态：

- `status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `negative_terms`
- `transcript_text`
- `captured_at`

### 8.3 turn 级复盘

统一读取：

```http
GET /api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle
```

读取：

- `text_features.primary_label`
- `text_features.primary_score`
- `text_features.top_3_labels`
- `text_features.negative_terms`

---

## 9. 端到端流程

当前文本模态实际流程应理解为：

```text
Browser
  -> upload audio
  -> multimodal-service audio-turns
  -> ASR transcript ready
  -> text emotion inference
  -> update live.text
  -> update turn_bundle.text_features
  -> consultation-service persists final business turn
  -> front-end reads live / bundle
```

在这个链路里，文本模态不是独立业务入口，而是语音主链中的正式副产物。

---

## 10. 前端显示方案

第一阶段右侧看板里，文本模态建议只显示：

- 主情绪标签
- 主分数
- 负向词项
- 正式 transcript 文本

不建议第一阶段加入：

- 复杂解释性文案自动生成
- 与风险结论混在一起的红黄绿判断
- 文本单模态直接输出临床级结论

原因是：

1. 当前文本模态只是数字人问诊阶段的语义副链
2. 它应先稳定成为标准结果层
3. 更强解释应交给上层服务完成

---

## 11. 当前最小实施步骤

### Step 0：先冻结业务边界

先明确本阶段不扩张的范围：

- 只覆盖数字人问诊阶段
- 只覆盖语音转写 transcript
- 不补 `manual_input -> text emotion`
- 不补量表问诊文本情绪

### Step 1：冻结文本标准输出契约

固定以下字段：

- `status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `negative_terms`
- `transcript_text`
- `captured_at`

### Step 2：确认 `audio-turns` 后的文本副链保持不变

保留现有成熟路径：

- `speech transcript -> text emotion`

不要因为文档整理而引入新的浏览器文本入口。

### Step 3：冻结 `live.text` 与 `bundle.text_features` 契约

建议明确：

- `live.text` 用于当前最新展示
- `bundle.text_features` 用于单轮正式结果
- 前端不从别处拼文本模态字段

### Step 4：补齐验收用例

至少验证：

1. 数字人问诊阶段语音回答后，文本情绪能进入 `live.text`
2. 数字人问诊阶段语音回答后，`turn_bundle.text_features` 可读取
3. `consultation_turn.transcript_text` 与文本模态使用的 transcript 一致
4. 页面刷新后，文本结果不丢
5. 前端不依赖假数据或手工拼接文本情绪结果

### Step 5：补齐上线后观测项

建议至少明确：

- 文本推理耗时怎么观察
- `live.text` 更新失败怎么排查
- bundle 中 `text_features` 缺失如何告警

---

## 12. 第一阶段完成边界

第一阶段完成的判断标准建议定为：

- 数字人问诊阶段语音转写后的文本情绪稳定输出
- `live.text` 与 `turn_bundle.text_features` 结构稳定
- 前端右侧看板统一消费文本标准结构
- 文本模态不再依赖前端临时拼接逻辑

第一阶段明确不做：

- `manual_input` 文本情绪识别
- 量表问诊文本情绪识别
- 复杂解释性文案自动生成
- 文本模态单独输出风险结论

---

## 13. 最终结论

在当前明确的业务边界下，文本模态最合理的方案不是扩展成“所有文本入口统一接入”，而是：

**把数字人问诊阶段的语音转写文本，稳定纳入现有 `multimodal-service` 副链，统一产出 `live.text` 与 `turn_bundle.text_features`。**

这套方案的核心原则是：

- 文本来源只认正式 ASR transcript
- 文本情绪推理归 `multimodal-service`
- 文本展示统一读 `live`
- 文本正式结果统一读 `bundle`
- 不把 `manual_input` 与量表问诊纳入当前范围

这样做的收益是：

- 与当前语音主链完全对齐
- 不额外扩张实现范围
- 更适合当前数字人问诊阶段交付目标
