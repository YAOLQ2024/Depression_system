# 面部情绪模态接入系统的代码对齐版实施方案

更新时间：2026-05-21

适用仓库：`depression-system`

---

## 1. 文档目标

本文档只聚焦一个模态：

- `face`

目标不是从零设计“面部情绪识别是否可做”，而是基于当前仓库已经存在的前后端代码，整理出一版可直接指导联调、补缺口和后续验收的接入方案。

本文档重点回答四个问题：

1. `face` 模态接入当前系统是否合理
2. 当前代码已经具备了哪些 face 接入骨架
3. `face` 在 `live / bundle / turn / capture` 体系里应该处于什么位置
4. 下一步应该补哪些缺口，才能把它变成稳定正式方案

本文档不展开：

- pose 模态细节
- face 模型训练与评估
- 多模态融合打分
- 风险服务消费逻辑

---

## 2. 先说结论

`face` 模态接入当前系统是合理的，但它的合理定位必须说清楚：

- 它适合作为 `伴随模态`
- 不适合作为 `问诊主输入模态`
- 它更适合 `高频连续采样`
- 它的单帧结果不适合直接当作最终问诊结论
- 它必须以 `turn 窗口聚合结果` 作为后续正式消费对象

一句话说：

**face 应该是一个“连续采样、逐帧推理、会话级实时展示、轮次级聚合归档”的视觉辅助模态。**

这和语音、文本很不一样：

- `speech / text` 更像一轮一结果
- `face` 更像一轮多帧、最终聚合

所以 face 的合理接入方式，不是给它造一套独立业务流程，而是接入当前已经存在的统一多模态骨架：

- `capture`
- `inference result`
- `live`
- `turn bundle`

如果从“是否走通”的角度定义，当前 face 更适合分成三个状态：

1. `已接入骨架`
   - 前端能采样
   - 服务端能推理
   - `live` 能更新

2. `已联调可演示`
   - `bundle.face_features` 可读取
   - 前端能展示实时结果
   - 基本链路能稳定跑完

3. `正式走通`
   - 契约冻结
   - 聚合口径冻结
   - 质量规则明确
   - 失败态可观测
   - 留档与复盘链路完整

本文档的目标是指导 face 从“已接入骨架”推进到“正式走通”。

---

## 3. 为什么 face 模态接入是合理的

### 3.1 它和问诊场景天然匹配

患者在回答问题时，面部表情会随着情绪、紧张程度、回忆负担和表达状态持续变化。

因此对问诊场景来说，face 的价值通常不在于：

- “这一帧绝对判定患者就是某种情绪”

而在于：

- 在一轮回答时间窗内，观察表情分布是否稳定
- 看有没有明显负向情绪偏移
- 作为 speech / text 之外的辅助证据

这和数字问诊尤其契合，因为问诊天然就是按题目、按轮次推进的，正好适合把 face 放进 `turn window` 的时间边界里理解。

### 3.2 它适合当前前端的摄像头持续采样机制

当前前端已经不是“拍一张照做一次识别”，而是在问诊时开启摄像头并持续截帧上传。

这非常适合 face 模态，因为：

1. 表情本来就是连续变化信号
2. 单帧误差很常见，多帧汇总更稳
3. 可以天然做 `label_distribution`
4. 可以天然统计质量问题，例如 `no_face`

### 3.3 它适合当前多模态分层结构

face 的合理性还体现在它和当前系统结构是对齐的：

- 原始输入是帧图像，天然对应 `capture`
- 每帧推理输出天然对应 `inference result`
- 最近结果天然适合 `live.face`
- 一轮多帧汇总天然适合 `bundle.face_features`

也就是说，face 并不需要额外发明一套新对象模型，它本身就适合放进当前已经存在的统一多模态骨架。

---

## 4. 当前代码里的真实 face 链路

### 4.1 前端采样方式

当前问诊页已经在录音回答窗口内持续截取摄像头帧，并同时提交 `face` 和 `pose`。

实际流程是：

1. 浏览器从摄像头取一帧
2. 生成 `image_file`
3. 组装：
   - `question_key`
   - `turn_id`
   - `sample_started_at`
   - `sample_ended_at`
   - `sample_index`
   - `mime_type`
4. 调用 `submitConsultationFaceCapture`

这说明 face 当前已经不是“规划中”，而是已经接入真实前端采样链路。

### 4.2 consultation-service 的职责

`consultation-service` 在 face 链路里不做模型推理。

它当前负责：

1. 校验 session 权限
2. 绑定或创建 `multimodal_session_id`
3. 把 face 捕获请求转发给 `multimodal-service`
4. 如果当前请求带 `turn_id`，把返回的 `turn_bundle` 缓存到 `consultation_turn.turn_summary_payload`

这层职责划分是合理的，因为它保持了：

- `consultation-service` 负责业务编排
- `multimodal-service` 负责模态推理

### 4.3 multimodal-service 的职责

当前 `multimodal-service` 已经具备完整的 face 处理骨架：

1. 记录一次 `face` capture
2. 调用 `infer_face_emotion`
3. 规范化推理结果
4. 写入 inference result
5. 刷新 `live.face`
6. 若有 `turn_id`，则更新该轮 `turn_bundle`

这意味着 face 并不是停留在“只做接口占位”，而是已经走到了：

- 有输入
- 有推理
- 有会话级输出
- 有轮次级聚合

### 4.4 当前 live 中的 face

当前 `live.face` 已经可以承载以下信息：

- `status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `quality_flags`
- `sample_started_at`
- `sample_ended_at`

这很适合前端右侧状态看板实时显示“最近一次 face 结果”。

### 4.5 当前 bundle 中的 face

当前 `turn_bundle` 里已经聚合 `face_features`。

它的定位不是最近一帧，而是：

- 某一轮回答窗口内多帧 face 结果的汇总

这是 face 模态最关键的一点，因为单帧结果波动很大，而 turn 聚合才适合作为正式消费结果。

---

## 5. 当前 face 结果结构的理解方式

### 5.1 单帧结果

当前 face 单帧推理结果已经被标准化为统一结构，核心包括：

- `modality = face`
- `status`
- `processing_status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `quality_flags`
- `sample_started_at`
- `sample_ended_at`
- `sample_index`

这说明 face 模态现在已经不是“裸模型输出”，而是经过服务层标准化了。

### 5.2 质量标记

当前 face 质量标记至少已经包含：

- `no_face`
- `blur`
- `low_light`

从当前实现看：

- `no_face` 已经进入标准结果、标签分布统计与质量分布统计
- `blur / low_light` 已经基于轻量图像规则参与标准结果输出
- 当前仍未形成更完整的质量筛选、降权或剔除机制

也就是说，当前 face 已具备基础质量标记能力，并已从“纯占位字段”推进到“可运行的轻量规则”；但它还没有形成完整的质量筛选、降权或剔除机制。

这套设计方向是合理的，因为 face 模态最怕的不是“模型没跑”，而是输入质量不稳定。

### 5.3 turn 级 face 聚合

当前 bundle 中的 `face_features` 更适合被理解为：

- 一轮回答窗口内 face 推理结果的统计摘要

按当前代码，聚合结果已经明确包含：

- `summary_type = turn_window`
- `primary_label`
- `primary_score`
- `primary_ratio`
- `sample_count`
- `valid_sample_count`
- `label_distribution`
- `quality_distribution`
- `quality_flags`

如果后续为了表达更业务化，想引入例如：

- `dominant_label`
- `quality_flags_ratio`
- `window_started_at`
- `window_ended_at`

建议明确标注为“目标态扩展字段”，不要与当前已实现 bundle 契约混写。

---

## 6. face 在当前系统里的合理定位

### 6.1 它不是业务主输入

对当前问诊系统来说，主输入仍然是：

- speech
- text

face 的角色更像辅助观察。

原因很简单：

1. 患者可能短时离开镜头
2. 面部遮挡非常常见
3. 表情受光照、角度、摄像头质量影响大
4. 单靠 face 不适合作正式临床语义输入

因此不能把 face 设计成“阻塞式主链”，例如：

- 没识别到 face 就不允许提交本轮回答

这是不合理的。

### 6.2 它应该是 sidecar 模态

更合适的方式是：

- 问诊主流程继续由 speech / text 驱动
- face 在用户回答过程中并行采样
- 不阻塞 turn 正常提交
- 成功时为 bundle 增强一层视觉证据

这和当前代码方向是一致的。

### 6.3 它的正式消费对象应该是 bundle，不是单帧

face 合理接入的前提是：

- `live.face` 给实时看板
- `bundle.face_features` 给正式消费

不能让后续风控或论文分析直接依赖最近一帧结果，因为那样波动太大、解释性太差。

---

## 7. 当前方案里已经做对的地方

### 7.1 用持续采样，而不是单张快照

这是正确方向。

face 模态最怕单张快照误判，而持续采样后再聚合更稳。

### 7.2 把推理放在 multimodal-service

这也是正确方向。

face 模型本质上属于模态服务，不应该侵入 `consultation-service`。

### 7.3 已经形成 live + bundle 双输出

这点非常关键。

如果只有 live，没有 bundle，face 就只能做“即时展示”，无法做正式回溯。

如果只有 bundle，没有 live，face 又失去实时感知价值。

当前两者兼有，方向是对的。

### 7.4 已经引入质量标记

这是视觉模态必须做的事情。

当前 `no_face / blur / low_light` 已进入标准结果结构，其中 `blur / low_light` 已有轻量规则；后续更适合继续增强精度，而不是再回到“先补字段占位”的阶段。

---

## 8. 当前 face 接入还存在的缺口

### 8.1 原始帧没有形成稳定留档策略

当前 capture 里已记录元数据，但原始 face 图像本体是否长期保存、是否上传对象存储、如何命名、是否支持回放，这些还不够明确。

这会影响：

- 调试
- 误判复盘
- 训练数据回看
- 论文截图追溯

### 8.2 `blur / low_light` 还需要从轻量规则继续增强

当前质量体系方向是对的，而且轻量规则已经落地；但如果后续要正式更强地消费 face 结果，建议继续增强：

- 模糊检测
- 低照度检测
- 可选的人脸面积过小检测

否则质量统计会看起来完整，实际上信息量不够。

### 8.3 face 的 turn 聚合口径需要文档固定

虽然当前已有 `face_features` 聚合，但还需要在文档层彻底写死：

- dominant label 怎么定
- label distribution 怎么算
- `no_face` 帧是否参与分母
- 低质量帧是否剔除
- 最小样本数门槛是多少

这几个规则如果不固定，后面联调和论文结果都容易口径不一致。

### 8.4 前端对 bundle 的消费仍偏弱

当前前端对 `live.face` 的消费已经比较明确，但 `turn_bundle.face_features` 的复盘路径还不够强。

这意味着 face 现在更像“实时展示功能”，还没有完全成为“每轮正式结果”的前端体验。

---

## 9. face 模态的推荐正式方案

### 9.1 写路径

推荐继续保持现有主方向：

```text
camera frame
  -> consultation-service capture endpoint
  -> multimodal-service face inference
  -> capture record
  -> inference result
  -> live.face
  -> turn_bundle.face_features
  -> consultation_turn.turn_summary_payload cache
```

不建议改成：

- 先把所有帧存满，再离线统一跑
- 或者把 face 逻辑挪进 `consultation-service`

### 9.2 读路径

推荐明确分层：

- 右侧状态看板：读 `live.face`
- 单轮复盘：读 `turn_bundle.face_features`
- 业务详情：仍以 `consultation_turn` 为主轴

### 9.3 数据契约

建议 face 标准结果至少固定如下字段：

- `status`
- `processing_status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `quality_flags`
- `sample_started_at`
- `sample_ended_at`
- `sample_index`

turn 聚合结果建议固定如下字段：

- `summary_type`
- `primary_label`
- `primary_score`
- `primary_ratio`
- `sample_count`
- `valid_sample_count`
- `label_distribution`
- `quality_distribution`
- `quality_flags`

如果后续为了增强业务可读性，可以再补充目标态扩展字段，例如：

- `dominant_label`
- `window_started_at`
- `window_ended_at`

但这些扩展字段不应在当前阶段写成“已实现正式契约”。

### 9.4 成功与失败边界

face 不应成为 turn 提交阻塞项。

推荐规则：

1. `face` 成功识别
   - 更新 live
   - 更新 bundle

2. `face` 无人脸
   - 记为有效采样但低价值结果
   - 保留 `no_face`
   - 不阻塞主流程

3. `face` 推理失败
   - 当前代码已可产出显式 `failed` 状态与 `error_message`
   - 不阻塞本轮问诊提交

因此更准确的现状描述是：

- 当前实现已经区分 `ok / no_face / failed`
- 后续更适合补强的是失败告警、回归测试与运行期观测，而不是再从字段层重做失败态

这和 face 的辅助模态定位是一致的。

---

## 10. 推荐的实施顺序

这一章的目标不是只描述“可以做什么”，而是给出一条可以执行的 face 走通路径。

建议把 face 接入走通拆成 4 个阶段：

### Phase A：骨架确认

目标：

- 确认当前链路已经具备最小闭环

完成标准：

- 前端能持续上传 face 帧
- `multimodal-service` 能产出单帧结果
- `live.face` 能更新

### Phase B：契约冻结

目标：

- 冻结单帧结果与 turn 聚合结果字段

完成标准：

- 前后端对 `live.face` 字段无歧义
- `bundle.face_features` 字段无歧义

### Phase C：正式化补齐

目标：

- 把质量规则、失败态、留档、复盘链路补完整

完成标准：

- face 结果具备稳定解释口径
- 出问题时可排查
- 页面刷新和单轮复盘都能恢复

### Phase D：交付验收

目标：

- 让 face 可以被正式宣称“接入走通”

完成标准：

- 验收清单全部通过
- 运行观测项可见
- 不再依赖临时假设或人工解释字段

### 当前实施进度（截至 2026-05-21）

按本文档的阶段划分，当前 face 已经基本完成：

- `Phase A：骨架确认`
- `Phase B：契约冻结`

并已进入：

- `Phase C：正式化补齐`

当前代码侧已具备的能力包括：

- 前端持续上传 face 帧
- `multimodal-service` 产出单帧标准结果
- face 推理失败时可产出显式 `failed` 结果
- `live.face` 实时更新，并带有 `processing_status / sample_count / valid_sample_count / error_message`
- `turn_bundle.face_features` 聚合生成
- `consultation_turn.turn_summary_payload` 缓存 bundle
- 原始 face 帧已开始写入对象存储引用 `storage_uri`
- 前端状态面板已优先消费当前轮 `bundle.face_features`
- 页面进入当前轮时会主动拉取 `turn bundle`
- 前端 `typecheck` 与生产构建已通过
- `multimodal-service` 的 face/live/bundle 路由 smoke test 已通过
- `multimodal-service` 的 face 服务层单元测试已通过
- `consultation-service` 的 face bundle 缓存单元测试已通过
- 当时曾提供 face 分服务验收脚本，现已移除

当前仍属于待补齐项的主要是：

- 带真实数据库、对象存储与模型资源的全链路联调
- 更完整的后端回归覆盖，例如数据库真实持久化与对象存储异常场景
- 运行期观测与清理策略的正式落地
- 如需更严格质量控制，可继续增强 `blur / low_light` 规则

### Step 0：先确认当前基线与不改动边界

在开始补方案之前，建议先冻结当前不准备在本阶段推翻的事实：

- 前端继续按当前持续截帧链路上传
- `consultation-service` 继续只做转发与业务缓存
- `multimodal-service` 继续负责 face 推理、live 更新、bundle 聚合
- face 当前仍是辅助模态，不阻塞 turn 主流程

这一步的作用是避免后续在实施中途又回到“大改架构还是小步补齐”的争论。

### Step 1：冻结 face 标准输出契约

优先把单帧结果和 turn 聚合结果字段名固定下来，并明确区分：

- 当前代码已实现字段
- 后续目标态扩展字段

建议至少冻结以下两组契约：

1. 单帧结果：
   - `status`
   - `processing_status`
   - `primary_label`
   - `primary_score`
   - `top_3_labels`
   - `quality_flags`
   - `sample_started_at`
   - `sample_ended_at`
   - `sample_index`

2. turn 聚合结果：
   - `summary_type`
   - `primary_label`
   - `primary_score`
   - `primary_ratio`
   - `sample_count`
   - `valid_sample_count`
   - `label_distribution`
   - `quality_distribution`
   - `quality_flags`

### Step 2：补齐质量规则

至少明确：

- `no_face`
- `blur`
- `low_light`
- 是否增加 `small_face`

同时建议把规则写成可执行口径：

- `no_face` 是否计入 `sample_count`
- `no_face` 是否计入 `valid_sample_count`
- `blur / low_light` 是否只统计，还是会影响聚合
- 哪些质量项只做展示，哪些质量项会影响后续消费

### Step 3：冻结 turn 聚合口径

明确：

- 哪些帧参与聚合
- 质量差帧是否降权或剔除
- `primary_label` 的决策规则
- `primary_score` 的含义是“主标签比例”还是“模型分数”
- `label_distribution` 的分母是 `sample_count` 还是 `valid_sample_count`

按当前代码，建议文档先与现实现保持一致：

- `label_distribution` 分母基于 `valid_sample_count`
- `quality_distribution` 分母基于 `sample_count`
- `primary_score` 当前等于 `primary_ratio`

### Step 4：补齐原始帧留档策略

明确：

- 是否上传对象存储
- 保存多久
- 如何命名
- 是否允许后续回看

还建议补两条：

- 数据库中只保留 `storage_uri` 和轻量元数据，不保留大图像正文
- 是否需要对 face 原始帧做抽样留档，而不是全量永久保存

### Step 5：补齐前端复盘消费

让页面不只显示当前 `live.face`，还要能在单轮层面读出 `bundle.face_features`。

同时应明确：

- 当前状态看板继续读 `live.face`
- 页面刷新恢复时可通过 `consultation_turn.turn_summary_payload` 或 turn bundle 接口恢复
- 复盘页或调试页不要直接扫 `capture` 明细表

### Step 6：补齐验收项

验收建议至少覆盖：

1. 摄像头开启后能持续上传 face 帧
2. `multimodal-service` 能成功写 capture
3. face 模型能返回标准化单帧结果
4. `live.face` 能持续刷新
5. turn bundle 能产出 `face_features`
6. `no_face` 情况不会阻塞问诊主流程
7. 刷新页面后仍能恢复 session live
8. 指定 turn 能读取 face 聚合结果

还建议再补四项：

9. `consultation_turn.turn_summary_payload` 能收到 face bundle 缓存
10. `label_distribution / quality_distribution` 口径与文档一致
11. `blur / low_light` 未启用时，前后端不会误判为已具备完整质量筛选
12. face 推理异常时，不会导致 consultation turn 提交链路中断
13. 前端 `typecheck` 通过，face 新增状态字段无类型错误
14. 前端生产构建通过，页面刷新后当前轮 `bundle.face_features` 可恢复并优先展示

### Step 7：补齐上线后的观测与回收策略

建议在交付前就明确以下运行项：

- face capture 每分钟写入量如何统计
- `no_face` 比例如何统计
- face 推理耗时如何观察
- bundle 生成失败时如何告警
- capture / inference_result 的保留周期和清理任务何时启用

这样实施步骤才不只覆盖“开发完成”，还能覆盖“上线后可持续运行”。

### Step 8：把实施步骤映射成可排期任务

建议在进入正式开发排期前，把每个步骤都映射成固定执行单元：

- 负责人
- 涉及服务
- 产出物
- 验收方式

推荐最小排期表如下。

| Step | 目标 | 负责人建议 | 涉及服务 | 主要产出物 | 验收方式 |
| --- | --- | --- | --- | --- | --- |
| Step 0 | 冻结当前基线与不改动边界 | 架构负责人 / 后端负责人 | consultation-service, multimodal-service, front-end | 基线确认记录、范围说明 | 评审会确认“本阶段不推翻现链路” |
| Step 1 | 冻结 face 单帧与 turn 聚合契约 | 后端负责人 | multimodal-service, consultation-service | 契约文档、字段清单、前端类型约定 | 前后端按同一字段样例联调通过 |
| Step 2 | 明确质量规则 | 算法负责人 + 后端负责人 | multimodal-service | 质量规则说明、字段语义表 | `no_face/blur/low_light` 语义一致，无歧义 |
| Step 3 | 冻结 turn 聚合口径 | 算法负责人 + 后端负责人 | multimodal-service | 聚合规则说明、示例 bundle | 同一批样本复算结果一致 |
| Step 4 | 明确原始帧留档策略 | 后端负责人 / 平台负责人 | multimodal-service, object storage | 存储路径规范、保留周期策略 | 样本帧可追溯，数据库不保存大对象正文 |
| Step 5 | 补齐前端复盘消费 | 前端负责人 | front-end, consultation-service | 状态看板读取说明、复盘读取说明 | `live.face` 与 `bundle.face_features` 都可被 UI 正确消费 |
| Step 6 | 补齐验收项 | 测试负责人 + 前后端共同参与 | all | 验收清单、联调记录 | 12 项验收项逐条通过 |
| Step 7 | 补齐运行期观测与回收 | 后端负责人 / 运维负责人 | multimodal-service, DB, object storage | 指标清单、告警规则、清理策略 | 能看到写入量、`no_face` 比例、推理耗时与清理任务状态 |

如果团队资源允许，建议把 Step 1、2、3 视为同一批“契约冻结阶段”，先整体过完评审，再进入开发；不要边改字段边写前端展示。

---

## 11. “走通”判定标准

如果项目里要明确宣布“face 模态接入已经走通”，建议至少同时满足下面 5 条：

1. 采样走通
   - 数字人问诊阶段摄像头开启后，face 帧能持续上传

2. 推理走通
   - `multimodal-service` 能稳定返回 face 单帧标准结果

3. 展示走通
   - `live.face` 能被前端状态看板稳定消费

4. 归档走通
   - `turn_bundle.face_features` 能稳定生成并被读取
   - `consultation_turn.turn_summary_payload` 能缓存 bundle

5. 复盘走通
   - 页面刷新后结果不丢
   - face 结果的字段口径、质量口径、失败口径都可解释

6. 静态校验走通
   - 前端 `typecheck` 通过
   - 前端生产构建通过
   - 后端至少完成语法编译检查

如果只满足前 2-3 条，更准确的表述应是：

- “face 已接入并可联调”

而不是：

- “face 已正式走通”

---

## 12. 不建议采用的接入方式

下面几种方案不建议走：

### 12.1 把 face 当主输入模态

这会导致：

- 镜头问题直接影响问诊流程
- 系统鲁棒性显著下降

### 12.2 只保留单帧 live，不做 turn 聚合

这会导致：

- 无法复盘
- 无法稳定用于后续融合
- 论文结果解释性差

### 12.3 把所有视觉逻辑塞进 consultation-service

这会导致：

- 服务职责混乱
- 推理依赖污染业务服务
- 后续 pose 接入也会更乱

### 12.4 不做质量标记直接消费结果

这会导致：

- 无人脸帧和有效帧混在一起
- 结果稳定性明显变差

---

## 13. 最终结论

当前仓库里的 face 模态接入方向总体是合理的，而且已经不只是概念设计，而是具备了：

- 前端持续采样
- consultation-service 转发
- multimodal-service 推理
- `live.face` 实时更新
- `turn_bundle.face_features` 聚合归档

当前最需要做的不是推翻重来，而是把这条链路补成正式方案：

- 固定 face 契约
- 固定 turn 聚合口径
- 补齐质量规则
- 补齐原始帧留档
- 强化 bundle 复盘消费

如果一句话总结这份方案，就是：

**face 应作为问诊过程中的高频视觉辅助模态，实时结果进 live，正式结果进 bundle，不阻塞 turn 主流程，但为后续多模态理解提供稳定的轮次级视觉证据。**
