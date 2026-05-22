# 多模态存储与数据库设计方案

更新时间：2026-05-21

适用仓库：`depression-system`

---

## 1. 文档目标

本文档用于明确 `depression-system` 在四模态场景下的正式存储与数据库设计方案。

覆盖范围：

- `speech`
- `text`
- `face`
- `pose`

本文档重点解决五件事：

1. 当前系统中哪些数据应该进数据库
2. 哪些数据不应该直接进数据库
3. `session / turn / capture / inference / live / bundle` 各自职责是什么
4. 如何控制 `face / pose` 带来的高频读写压力
5. 后续推荐的索引、冷热分层、生命周期与演进路线是什么

---

## 2. 先说结论

这套系统最合理的数据库设计，不是：

- 把四模态结果都塞进 `consultation_turn`
- 或者给每个模态都单独造一整套业务表

而是采用统一分层设计：

1. `session / turn`
   - 保存业务真相

2. `capture / inference_result`
   - 保存高频模态明细

3. `live`
   - 保存会话级最新展示态

4. `bundle`
   - 保存轮次级正式归档态

5. `object storage`
   - 保存原始大对象

一句话总结：

**数据库负责保存结构化真相与聚合结果，对象存储负责保存原始大文件，高频明细层必须轻量化、可清理、不可成为主查询路径。**

---

## 3. 当前代码中的核心存储对象

从当前代码看，系统已经具备一套可用的多模态分层骨架：

- `consultation_sessions`
- `consultation_turns`
- `multimodal_captures`
- `multimodal_inference_results`
- `multimodal_turn_bundles`
- `consultation_sessions.multimodal_live_payload`

当前方向总体是对的，后续不建议推翻，只建议收紧职责边界、补齐索引和生命周期策略。

---

## 4. 统一设计原则

### 4.1 业务真相和模态真相分离

数据库设计首先要分清两类真相：

- 业务真相
  - 某次问诊
  - 某轮回答
  - 正式文本
  - 正式音频引用

- 模态真相
  - 某次采样
  - 某次推理
  - 某轮聚合结果

前者应主要落在：

- `consultation_sessions`
- `consultation_turns`

后者应主要落在：

- `multimodal_captures`
- `multimodal_inference_results`
- `multimodal_turn_bundles`

### 4.2 高频写和正式读分离

`face / pose` 最大的数据库风险不是查询，而是持续采样带来的高频写入。

因此必须分层：

- 高频写入层：
  - `capture`
  - `inference_result`

- 正式读取层：
  - `live`
  - `bundle`
  - `turn`

不能让前端和下游分析频繁扫高频明细表。

### 4.3 大对象不进数据库

数据库不是原始大对象仓库。

以下内容不建议直接放数据库：

- 原始音频文件
- 标准化 wav 文件
- 原始 face 图像
- 原始 pose 图像
- base64 大字段

这类数据应进入对象存储，数据库只保存：

- `storage_uri`
- 元数据
- 必要索引字段

### 4.4 bundle 是正式消费入口

如果后续要做：

- 每轮复盘
- 多模态融合
- 风险服务消费
- 论文统计

正式入口应优先是 `turn_bundle`，而不是 `capture` 明细表。

---

## 5. 分层对象职责

## 5.1 `consultation_sessions`

职责：

- 保存问诊会话业务主状态
- 保存当前题目与流程上下文
- 缓存会话级 `multimodal_live_payload`

适合保存：

- `user_id`
- `workflow_id`
- `current_stage_id`
- `current_question_key`
- `status`
- `multimodal_session_id`
- `multimodal_live_payload`
- `multimodal_live_updated_at`

不适合保存：

- face / pose 明细数组
- 多轮历史模态记录
- 原始大对象

设计建议：

- `multimodal_live_payload` 保持为小型快照
- 不把历史记录堆进 `session` JSON
- 后续并发上来后，`live` 可考虑迁移到 Redis，数据库只保留最终快照

## 5.2 `consultation_turns`

职责：

- 保存一轮问答的正式业务真相

适合保存：

- `session_id`
- `stage_id`
- `question_key`
- `input_type`
- `raw_input`
- `audio_uri`
- `original_audio_uri`
- `normalized_wav_uri`
- `transcript_text`
- `transcript_source`
- `response_started_at`
- `response_completed_at`
- `turn_summary_payload`

不适合保存：

- face/pose 单帧推理结果
- 高频采样明细
- 原始图像大对象

设计建议：

- `turn_summary_payload` 只作为 bundle 缓存，不要演化成明细仓
- `consultation_turns` 永远围绕业务轮次，不承载所有模态细节

## 5.3 `multimodal_captures`

职责：

- 保存一次原始采样事件的轻量元数据

适合保存：

- `session_id`
- `turn_id`
- `flow_run_id`
- `question_key`
- `modality`
- `sample_index`
- `sample_started_at`
- `sample_ended_at`
- `storage_uri`
- `capture_kind`
- `captured_at`
- 必要轻量 `capture_payload`

不适合保存：

- 整张图片原文
- 大段 base64
- 可从对象存储或其他字段重复推导的大块数据

设计建议：

- `capture_payload` 只保留元信息
- 真正的大对象放对象存储
- 这张表是事件表，不是前端主查询表

## 5.4 `multimodal_inference_results`

职责：

- 保存一次模态推理的标准化结果

适合保存：

- `session_id`
- `turn_id`
- `sample_id`
- `modality`
- `source_kind`
- `source_ref_id`
- `captured_at`
- 标准化 `inference_payload`

建议标准化 payload 至少包含：

- `primary_label`
- `primary_score`
- `top_3_labels`
- `status`
- `processing_status`
- `quality_flags`

设计建议：

- 保留“标准化结果”，不要依赖裸模型返回结构
- 保持单行轻量
- 它是中间层明细表，不是正式下游读取入口

## 5.5 `multimodal_turn_bundles`

职责：

- 保存某一轮问答的多模态正式聚合结果

适合保存：

- `session_id`
- `turn_id`
- `flow_run_id`
- `question_key`
- `bundle_payload`

建议 bundle 包含：

- `speech_features`
- `text_features`
- `face_features`
- `pose_features`

设计建议：

- 每个 `session_id + turn_id` 只保留一条正式 bundle
- bundle 是正式消费层
- 前端单轮复盘、后续风控与统计优先读它

---

## 6. 哪些数据应该进对象存储

以下数据应优先进入对象存储，而不是数据库大字段：

### 6.1 音频类

- 浏览器原始上传音频
- 标准化 `wav`

### 6.2 图像类

- face 原始帧图像
- pose 原始帧图像

### 6.3 后续可扩展

- 人工复核截图
- 调试导出图像
- 可视化分析中间产物

数据库里建议只保留：

- `storage_uri`
- 文件格式
- 文件大小
- 采样时间
- 所属 `session / turn / modality / sample_index`

---

## 7. 数据库压力主要来自哪里

要明确，当前系统的数据库压力并不是平均分布的。

### 7.1 低压层

- `consultation_sessions`
- `consultation_turns`
- `multimodal_turn_bundles`

这些表的写入频率都不高：

- session：每次问诊几次更新
- turn：每轮一次
- bundle：每轮一条或少量更新

### 7.2 中压层

- `multimodal_live_payload`

它会随会话过程不断更新，但本质是覆盖写，不是无限累积写。

### 7.3 高压层

- `multimodal_captures`
- `multimodal_inference_results`

特别是：

- `face`
- `pose`

因为它们是连续采样、多帧写入，所以这两张表才是数据库设计里的真正高压区。

---

## 8. face / pose 高压区的控压策略

### 8.1 控制采样频率

最直接有效的办法就是限频。

建议第一阶段采样频率不要过高，例如：

- `1~2 fps`

不建议一开始就做高频连续帧入库。

### 8.2 capture 只保留轻量元数据

`capture_payload` 里不要放：

- base64 原文
- 过长嵌套对象

建议只放：

- mime/type
- image_format
- sample_index
- image_size 或长度
- 质量信息

### 8.3 inference_result 只保留关键标准结果

不要把整个模型长结果原封不动灌进库里。

建议只保留：

- 主标签
- 主分数
- top-k
- 质量标记
- 状态

### 8.4 正式读取不扫明细表

前端右侧面板：

- 读 `live`

单轮复盘和下游消费：

- 读 `bundle`

不要让前端直接分页或轮询扫 `capture` / `inference_result` 明细表。

### 8.5 给明细层设生命周期

建议一开始就制定保留策略：

- `capture`：7~30 天
- `inference_result`：30~90 天
- `bundle / turn / session`：长期保留

如果没有这个策略，视觉模态会让数据库体量持续膨胀。

---

## 9. 推荐索引方案

当前模型里很多字段已有单列索引，但面对高频查询，组合索引更关键。

推荐优先补以下索引。

## 9.1 `multimodal_captures`

推荐组合索引：

- `(session_id, modality, captured_at)`
- `(turn_id, modality, sample_index)`
- `(flow_run_id, question_key, modality)`

作用：

- 查某会话下某模态最近采样
- 查某轮某模态全部采样
- 查某题某模态窗口明细

## 9.2 `multimodal_inference_results`

推荐组合索引：

- `(session_id, modality, captured_at)`
- `(turn_id, modality, captured_at)`
- `(sample_id, modality)`
- `(flow_run_id, question_key, modality)`

作用：

- 查某轮某模态结果时间线
- 查某次采样对应推理
- 查某会话最近某模态结果

## 9.3 `multimodal_turn_bundles`

当前唯一约束：

- `(session_id, turn_id)`

建议继续保留，同时可补：

- `(flow_run_id, question_key)`

作用：

- 支持按问诊流程和题目查询 turn 聚合结果

## 9.4 `consultation_turns`

建议重点关注：

- `(session_id, turn_index)`
- `(consultation_flow_run_id, question_key)`
- `(encounter_session_id, created_at)`

作用：

- 按问诊顺序恢复轮次
- 按题目查正式业务 turn

---

## 10. JSON 字段使用边界

当前系统里 JSON 字段很多，因此必须明确边界，否则后面很容易失控。

### 10.1 适合放 JSON 的内容

- 结构会逐步演化的聚合结果
- top-k 列表
- 质量标记
- 小型配置快照
- 阶段性兼容字段

### 10.2 不适合放 JSON 的内容

- 高频大数组
- 原始大对象
- 大段 base64
- 前端展示缓存拼装历史
- 需要频繁按子字段做复杂过滤的核心事实

### 10.3 设计建议

规则应该是：

- 结构化主键、关联键、时间字段、模态字段单独列出
- 演化中的细节再放 JSON

不要把所有查询字段都藏进 JSON。

---

## 11. 推荐的冷热分层

### 11.1 热数据

用于当前问诊、当前前端、当前聚合：

- `consultation_sessions`
- `consultation_turns`
- `multimodal_turn_bundles`
- `live`

### 11.2 温数据

用于近期开调试、复盘、问题排查：

- `multimodal_inference_results`

### 11.3 冷数据

用于长期留档、必要时回看：

- 对象存储中的原始音频
- 标准化 wav
- 原始图像帧
- 必要调试导出

### 11.4 长期演进

当数据量进一步上来时，可考虑：

- 明细表按时间分区
- 历史明细归档到独立库或冷存
- `live` 迁移到 Redis

---

## 12. 推荐读写路径

### 12.1 写路径

统一建议：

```text
raw input
  -> object storage (large object)
  -> capture (metadata)
  -> inference_result (standardized result)
  -> live (latest state)
  -> turn_bundle (turn summary)
  -> consultation_turn (business truth / cache)
```

### 12.2 读路径

统一建议：

- 实时看板：读 `live`
- 单轮复盘：读 `bundle`
- 问诊业务主流程：读 `turn`
- 调试排查：必要时读 `capture / inference_result`

这样可以保证：

- 高价值查询稳定
- 高频明细不成为热点读源

---

## 13. 不建议的数据库设计方式

下面几种方式都不建议采用：

### 13.1 所有模态结果都塞进 `consultation_turn`

问题：

- turn 表会迅速膨胀
- 业务真相和模态明细混在一起
- 后续 face/pose 很难控压

### 13.2 每个模态单独造一套全量业务表

问题：

- 表数量暴涨
- 接口和代码重复
- 难以形成统一多模态契约

### 13.3 把原始帧和音频直接存数据库

问题：

- 存储膨胀快
- IO 压力高
- 迁移、备份、恢复都变重

### 13.4 让前端直接查高频明细表

问题：

- 查询路径不稳定
- 容易把数据库热点打到明细层

---

## 14. 推荐的演进路线

### Phase 1：保持现有 5 表骨架

保留：

- `consultation_sessions`
- `consultation_turns`
- `multimodal_captures`
- `multimodal_inference_results`
- `multimodal_turn_bundles`

### Phase 2：补索引与字段边界

完成：

- 高频表组合索引
- JSON 字段边界收紧
- 明细层轻量化

### Phase 3：补对象存储留档规范

完成：

- 音频命名规则
- 图像命名规则
- `storage_uri` 使用规范
- 原始对象保留周期

### Phase 4：补生命周期管理

完成：

- capture 清理任务
- inference_result 清理任务
- 冷热数据转移策略

### Phase 5：引入缓存层

当并发进一步上来时：

- `live` 优先迁移到 Redis
- 数据库只保留回写快照

### Phase 6：必要时对明细表做分区或归档

适用条件：

- face / pose 采样量明显增大
- 单表体量快速增长

---

## 15. 最终结论

当前这套多模态系统最合理的正式存储方案是：

- `session / turn` 负责业务真相
- `capture / inference_result` 负责高频明细
- `live` 负责会话级最新展示
- `bundle` 负责轮次级正式归档
- 原始音频和图像帧进入对象存储

数据库设计最关键的不是“能不能把所有数据都存下”，而是：

- 让高价值结果可稳定读取
- 让高频明细可控、可清理、可追溯
- 不让 `face / pose` 的持续采样把业务主库拖垮

如果一句话总结这份方案，就是：

**四模态场景下，应采用“业务真相、模态明细、实时快照、轮次归档、原始对象”五层分离的存储设计，其中高频明细层必须轻量化、限频、可清理，正式消费统一收敛到 `live + bundle + turn`。**
