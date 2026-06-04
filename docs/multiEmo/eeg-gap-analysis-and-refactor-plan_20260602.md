# EEG 现状问题、标准差距与 Redis 热链路接入方案

更新时间：2026-06-02

适用仓库：`depression-system`

适用范围：

- `services/multimodal-service`
- `services/consultation-service`
- `services/assessment-service`
- `apps/consultation`

---

## 1. 文档目的

这份文档回答 5 个问题：

1. 当前仓库里的 EEG 到底是怎么实现的。
2. 它和 `dev` 分支已经做过的 `face / pose` Redis 热链路有什么差别。
3. 当前 EEG 实现有哪些结构性问题和代码风险。
4. EEG 在本项目里应该保存什么，不应该保存什么。
5. 如果按现有 Redis 热链路基线接入 EEG，应该怎么落地。

本文只讨论工程接入，不讨论脑电模型本身的科学性。

---

## 2. 结论先行

本次方案确定采用 `dev` 分支已经实现过的 Redis 热链路作为基线，而不是当前审查分支中的退化实现。

EEG 的 P0 目标收敛为：

1. EEG 实时看板数据进入 Redis，只保留热态，用完即丢，不持久化到数据库。
2. EEG 原始数据只保存文件，不把完整波形写进数据库。
3. EEG 推理结果按 `window` 落 `multimodal_inference_results`。
4. EEG 不在 P0 中落 `turn summary`、`key windows`、`finalized hot-state artifact`。
5. turn 结束时只做 Redis 热态清理，不额外生成 EEG 的 bundle 持久化。

一句话概括：

`EEG = Redis 实时热态 + 原始文件冷存 + window 结果落库`

---

## 3. 当前 EEG 的真实实现方式

## 3.1 当前不是浏览器上传，而是服务进程自己连硬件

当前 EEG 不是通过统一的 HTTP capture 接口进入系统，而是：

1. `multimodal-service` 启动时自动启动两个后台任务：
   - BLE 自动扫描与接收
   - EEG 后台推理循环
2. 服务进程扫描蓝牙设备名里带 `EEG` 的设备
3. 连接固定特征 UUID
4. 解析两类数据包：
   - 波形包
   - 57 维特征包
5. 波形包进入 `_wave_buffer`
6. 特征包进入 `_feat_buffer`
7. 同时写本地 CSV
8. 推理线程每 10 秒取一次特征窗口做三分类推理
9. 推理结果 append 到 `multimodal_sessions.live_state_payload["eeg"]`
10. 前端通过 `/live` 或 `/live/stream` 读取 `eeg_waves` 与 `eeg`

这说明当前 EEG 是：

- 服务内置采集
- session 级 live payload 挂载
- 没有正式进入 Redis 热链路

## 3.2 当前关键代码入口

当前 EEG 主要分布在：

- `services/multimodal-service/app/main.py`
- `services/multimodal-service/app/services/eeg_ble_manager.py`
- `services/multimodal-service/app/services/eeg_inference_runtime.py`
- `services/multimodal-service/app/services/multimodal_session_service.py`
- `apps/consultation/client/src/components/ConsultationStatusPanel.tsx`

## 3.3 当前数据去向

当前 EEG 数据主要流向 3 个地方：

### A. 内存缓冲

- `_wave_buffer`
- `_feat_buffer`

用途：

- 实时波形展示
- 后台推理窗口消费

### B. 本地 CSV

- `eeg_waves_{session_id}.csv`
- `eeg_features_{session_id}.csv`

用途：

- 调试
- 本地留痕

### C. `multimodal_sessions.live_state_payload`

- `live_state_payload["eeg"]`

用途：

- 前端显示最近分类结果

当前 EEG 没有：

- Redis 热态
- 标准 raw file 冷存
- 标准 window 结果表

---

## 4. Face/Pose 的 Redis 热链路基线

这部分以 `dev` 分支中已经实现过的热路径为准。

## 4.1 已存在的视觉热链路结构

`face / pose` 在 `dev` 分支中的热链路核心包括：

- `visual live` Redis key
- turn aggregate Redis key
- turn frame Redis key
- turn candidate Redis key
- turn state Redis key
- Redis pub/sub SSE 推送
- coarse checkpoint
- turn finalize 时关键帧落库

核心文件包括：

- `services/multimodal-service/app/services/visual_turn_state_store.py`
- `services/multimodal-service/app/services/visual_key_frame_selector.py`
- `services/multimodal-service/app/services/multimodal_live_stream.py`

## 4.2 视觉热链路的真实职责边界

视觉热链路的职责是：

1. 把当前 turn 的连续采样结果放进 Redis
2. 支撑看板实时刷新
3. 支撑 SSE 推送
4. 维护 turn 级统计和候选关键帧
5. 在 finalize 时从 Redis 选关键帧并做最终持久化

其中：

- Redis 负责热态
- PostgreSQL 负责最终持久化
- MinIO 负责媒体对象

## 4.3 EEG 不照搬视觉 finalize，只复用热链路思想

EEG 与 `face / pose` 的最大不同是：

- `face / pose` 最终只需要保关键帧与推理摘要
- EEG 原始信号本身就是主证据，必须保原始文件

因此 EEG 应复用的是：

- Redis 热态
- SSE / live 机制
- turn 级热状态组织方式

而不是强行复用：

- 关键窗口持久化
- turn summary 落库
- finalized hot-state artifact 落库

---

## 5. 当前 EEG 的主要问题

## 5.1 会话归属问题

当前 EEG 使用全局 `_active_session_id` 决定数据归属，而这个值是在读取 `/live` 时通过 `set_active_session(session_id)` 切换的。

这会带来：

- 谁最后读了 `/live`，谁就可能接管 EEG 数据
- 并发 session 时数据可能串线
- 读操作带副作用
- turn 级别没有稳定绑定

这是当前 EEG 最大的架构风险。

## 5.2 没有 Redis 热态

当前 EEG 没有接入 `dev` 分支已经存在的 Redis 热链路，因此：

- 看板实时数据来源不统一
- SSE 机制无法复用正式热路径
- 当前波形与当前结果没有标准热态容器
- 热态和持久化职责混在 `live_state_payload` 与 CSV 里

## 5.3 原始数据保存方式不规范

当前只写本地 CSV，问题包括：

- 不适合多实例部署
- 不适合统一对象存储管理
- 不适合按 turn/window 检索
- 不适合作为正式证据链

## 5.4 推理结果没有标准 observation 落库

当前 EEG 推理结果没有按 `window` 写 `multimodal_inference_results`，导致：

- 下游无法按标准表查询 EEG
- 不能稳定按 `turn_id` 取 EEG window 结果
- 风险评估与后续模块无法统一消费

## 5.5 `/live` 与 `/live/stream` 的副作用和丢帧风险

当前存在两个问题：

1. `/live` 会切换 EEG 活跃 session
2. SSE 路径会双重消费 `eeg_waves`

结果是：

- 看板读取会改变系统状态
- 波形数据可能被提前清空
- 实时展示不稳定

## 5.6 EEG 现在不应该先做 bundle 化

当前已确认下游决策模块真正需要消费的是：

- EEG window 推理结果

而不是：

- EEG turn summary
- EEG key windows
- EEG finalized hot-state bundle

所以 EEG 继续朝“强行补 bundle”方向推进，会增加复杂度但短期没有收益。

---

## 6. 本次确定的 EEG P0 方案

## 6.1 保存边界

P0 明确采用下面的保存边界：

### 要保存

- 原始 EEG 文件
- EEG window 推理结果

### 不保存到数据库

- 实时波形预览
- 当前设备状态热态
- 当前窗口缓冲
- 当前 turn 的临时聚合热态

### 暂不做

- EEG turn summary 落库
- EEG key windows 落库
- EEG finalized hot-state artifact 落库

## 6.2 三层职责

### A. Redis 热态层

只负责：

- 看板实时波形
- 最近一次或最近几次推理结果
- 当前 turn 的热缓冲与状态

特点：

- 只保留短 TTL
- 用完即丢
- 不作为正式历史数据源

### B. 对象存储冷存层

只负责：

- 原始 EEG 文件

特点：

- 正式留档
- 可回放
- 可复核
- 可导出

### C. PostgreSQL 结果层

只负责：

- EEG 的 window 推理结果

特点：

- 下游标准消费
- 可按 turn 查询
- 不承载大体积原始信号

---

## 7. 推荐目标架构

## 7.1 总体流程

推荐流程如下：

1. turn 开始时，流程层显式开始 EEG 采集绑定
2. 采集线程持续接收 EEG 数据
3. 最近几秒波形预览写 Redis `live`
4. 按固定 window 形成原始 EEG 片段
5. 每个 window 的原始数据写对象存储
6. 每个 window 跑一次推理
7. 每个 window 的推理结果写 `multimodal_inference_results`
8. 最近一次或最近几次推理结果写 Redis `live`
9. turn 结束时清理 Redis 热态

这里没有要求：

- 生成 EEG turn summary
- 生成 EEG key windows
- 把 EEG 纳入 finalized bundle

## 7.2 为什么可以不做 turn summary / key windows 落库

原因有 4 个：

1. 当前下游消费目标已经明确是 window 结果，不是 EEG bundle。
2. EEG 原始信号已经全量保存文件，不像视觉那样必须靠关键帧降低存储量。
3. 先把“实时 + 冷存 + 结果表”跑通，收益最高、风险最低。
4. 将来如果 risk-service 明确要 turn-level EEG 聚合，再在 window 结果之上现算或补表更合适。

因此：

- P0 不做 EEG turn summary 落库是合理的。
- P0 不做 EEG key windows 落库也是合理的。

---

## 8. Redis 热链路设计

## 8.1 设计原则

EEG 的 Redis 热链路应满足：

1. 看板读取必须实时。
2. 看板读取不能改变 session 归属。
3. Redis 只保存热态，不保存长期历史。
4. Redis 结构要按 `session + turn` 组织。

## 8.2 推荐 Redis key

推荐 key 设计如下：

- `eeg:live:{session_id}`
- `eeg:turn:{session_id}:{turn_id}:state`
- `eeg:turn:{session_id}:{turn_id}:window:{window_index}`

如需保留极简候选集合，可预留：

- `eeg:turn:{session_id}:{turn_id}:candidate:{window_index}`

但 P0 可以先不启用 candidate 语义。

## 8.3 `eeg:live:{session_id}` 推荐内容

建议只保存看板所需轻量数据：

- `session_id`
- `turn_id`
- `updated_at`
- `device_status`
- `sampling_rate`
- `channel_names`
- `preview_waves`
- `latest_results`

其中：

- `preview_waves` 是最近几秒下采样预览
- `latest_results` 是最近一次或最近几次 window 推理结果

不应放入：

- 完整原始波形历史
- 全部特征历史
- 长列表 append 型结果

## 8.4 `eeg:turn:{session_id}:{turn_id}:state` 推荐内容

建议包含：

- `session_id`
- `turn_id`
- `status`
- `started_at`
- `last_updated_at`
- `window_count`
- `last_window_index`
- `last_window_started_at`
- `last_window_ended_at`

这里只保存 turn 热状态，不做 finalize 落库。

## 8.5 `eeg:turn:{session_id}:{turn_id}:window:{window_index}` 推荐内容

建议保存单个 window 的热态元信息：

- `session_id`
- `turn_id`
- `window_index`
- `sample_started_at`
- `sample_ended_at`
- `raw_eeg_uri`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `model_version`
- `quality_flags`

TTL 到期或 turn 结束后可直接删除。

## 8.6 SSE

EEG 可复用 `dev` 中已存在的 Redis pub/sub SSE 思路：

- 有热态变更时发布 live snapshot
- `/live/stream` 只推送快照
- 不从 SSE 路径直接消费底层原始波形缓冲

这能避免当前实现中的双重清空问题。

---

## 9. 原始 EEG 文件冷存方案

## 9.1 保存策略

原始 EEG 文件应当：

- 按 window 滚动保存
- 不等整个 turn 结束再一次性写
- 与推理窗口保持稳定对应关系

推荐 P0 直接采用：

- `1 raw file = 1 inference window`

也就是：

- 一个 `10s` window
- 一个原始文件
- 一次推理
- 一条结果表记录

这是 P0 最简单、最稳的映射关系。

## 9.2 为什么不建议只在 turn 结束时写一个大文件

因为那样会导致：

- 进程中断时丢整段数据
- 原始数据与推理窗口难以稳定映射
- 文件太大，不利于回放与排查

## 9.3 文件格式建议

P0 推荐使用：

- `npz`

理由：

- Python 生态直接支持
- 精度稳定
- 比 CSV 更适合数值型信号
- 实现复杂度低于 Parquet

## 9.4 文件内容建议

每个原始 EEG 文件建议至少包含：

- `samples`
- `channel_names`
- `sampling_rate`
- `sample_started_at`
- `sample_ended_at`
- `device_id`
- `window_index`
- `packet_loss_ratio`
- `quality_flags`

## 9.5 对象存储路径建议

建议对象路径采用：

`raw/eeg/{session_id}/{turn_id}/window-{window_index}.npz`

如果 turn 未绑定成功，不应继续采集写入正式路径，而应直接拒绝开启正式 EEG 采集。

---

## 10. EEG 推理结果落库方案

## 10.1 结果表

P0 明确采用：

- `multimodal_inference_results`

每个 EEG window 对应一条结果。

## 10.2 推荐字段语义

建议写入：

- `session_id`
- `turn_id`
- `flow_run_id`
- `stage_id`
- `question_key`
- `modality = "eeg"`
- `source_kind = "eeg_window"`
- `source_ref_id = raw file object key 或 window index`
- `captured_at = sample_ended_at`

`inference_payload` 建议包含：

- `window_index`
- `sample_started_at`
- `sample_ended_at`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `model_name`
- `model_version`
- `raw_eeg_uri`
- `quality_flags`

## 10.3 是否需要 `multimodal_captures`

P0 可以有两种做法：

### 方案 A：极简做法

不新增 EEG capture 记录，只保存：

- 原始文件
- inference result

优点：

- 改动最小
- 最符合当前“下游只消费推理结果”的目标

缺点：

- 缺少统一 capture 追踪层

### 方案 B：标准做法

每个 window 同时写一条 `multimodal_captures`：

- `modality = "eeg"`
- `capture_kind = "window"`
- `storage_uri = raw_eeg_uri`

优点：

- 和其他模态结构一致
- 原始文件与结果更容易对齐

缺点：

- 改动稍大

本次 P0 推荐：

- 如果时间紧，先做方案 A
- 如果允许一步到位，优先方案 B

---

## 11. 是否需要 EEG turn summary、key windows、hot-state 收口落库

结论：

- P0 不需要

## 11.1 turn summary

当前不建议落库，因为：

- 下游当前不直接消费 EEG turn summary
- 可以在需要时由 window 结果现算
- 过早建 turn summary 只会增加维护负担

## 11.2 key windows

当前不建议落库，因为：

- EEG 原始文件已经全量保存
- 不需要像视觉那样靠关键帧降低存储体积
- 关键窗口选择规则短期没有明确业务收益

## 11.3 finalized hot-state artifact

当前不建议落库，因为：

- 热态本来就是给实时看板用的
- turn 结束后只需要清理 Redis
- 没必要把热态再做一份 finalize 持久化

## 11.4 什么时候再考虑加这些能力

只有在出现以下明确需求时，再进入 P1/P2：

- risk-service 明确要求 turn-level EEG 聚合输入
- 需要 EEG 重点窗口回顾
- 需要 EEG 多窗口摘要解释
- 需要 EEG 与视觉一样进入统一 finalized bundle

---

## 12. 服务职责建议

## 12.1 `multimodal-service`

负责：

- EEG turn 绑定与生命周期
- EEG 实时预览 Redis 写入
- EEG raw file 滚动写对象存储
- EEG window 推理
- EEG window 推理结果落库
- EEG Redis 热态清理
- EEG SSE / live 输出

不负责：

- 通过读 `/live` 决定 session 归属
- 把 EEG 历史结果 append 到 session JSON

## 12.2 `consultation-service`

负责：

- 在问诊回答窗口开始时触发 EEG turn 开始
- 在回答窗口结束时触发 EEG turn 结束
- 读取 `/live` 用于看板展示

## 12.3 `assessment-service`

负责：

- 在量表题目回答窗口开始时触发 EEG turn 开始
- 在题目结束时触发 EEG turn 结束
- 读取 EEG window 结果供量表阶段下游流程使用

## 12.4 `apps/consultation`

负责：

- 只消费 Redis live 输出的 EEG 预览
- 不直接依赖 session JSON 历史 append
- 不要求 bundle 中必须有 `eeg_features`

---

## 13. 前端改动建议

## 13.1 看板只看 live

前端 EEG 看板只应依赖：

- `multimodal_live.eeg_live`
- `multimodal_live.eeg_waves`

其中：

- `eeg_waves` 是短时预览
- `eeg_live` 是最近状态与最近结果

## 13.2 不再把 EEG 视为 bundle 模态

P0 前端不需要：

- `current_turn_bundle.eeg_features`
- EEG finalized summary
- EEG key window 回顾

## 13.3 类型定义要正式化

当前前端通过 `as any` 读 EEG，不够稳定。

P0 需要补正式类型：

- `EegWavePreview`
- `EegLiveResult`
- `EegLivePayload`

---

## 14. 按现有 Redis 热链路基线的落地步骤

## Phase 1：去掉当前错误归属方式

目标：

- 不再用读 `/live` 来绑定 EEG session

步骤：

1. 移除 `get_multimodal_live()` 中的 `set_active_session(session_id)`
2. 新增显式的 EEG turn 开始 / 结束内部服务函数
3. 把 EEG 归属改成由流程事件驱动

完成标准：

- 读取 live 不再改变 EEG 状态

## Phase 2：补 Redis 热态

目标：

- 让 EEG 看板正式进入 Redis 热路径

步骤：

1. 新增 EEG Redis key 读写模块
2. 在采集线程中持续更新：
   - `eeg:live:{session_id}`
   - `eeg:turn:{session_id}:{turn_id}:state`
   - `eeg:turn:{session_id}:{turn_id}:window:{window_index}`
3. `/live` 改为优先读 EEG Redis 热态
4. `/live/stream` 改为走 Redis pub/sub 快照

完成标准：

- 前端看板看到的是 Redis 中的 EEG 实时态

## Phase 3：补原始文件冷存

目标：

- 让 EEG 原始数据从本地 CSV 改为正式对象存储

步骤：

1. 定义 raw EEG window 文件结构
2. 按 window 滚动写 `npz`
3. 上传 MinIO
4. 保留 `raw_eeg_uri`
5. 停止把 CSV 作为主数据路径

完成标准：

- 每个推理窗口都有原始文件可回溯

## Phase 4：按 window 落推理结果

目标：

- 让 EEG 成为正式可查询模态结果

步骤：

1. 每个 EEG window 推理后写 `multimodal_inference_results`
2. payload 包含 `raw_eeg_uri`
3. 统一带上：
   - `session_id`
   - `turn_id`
   - `flow_run_id`
   - `stage_id`
   - `question_key`

完成标准：

- 下游可按 `turn_id` 查询 EEG window 结果

## Phase 5：turn 结束只清 Redis

目标：

- 收束热态，但不增加不必要持久化

步骤：

1. turn 结束后删除或等待 TTL 清理 EEG 热态 key
2. 不生成 EEG turn summary
3. 不生成 EEG key windows
4. 不把 EEG 纳入 finalized bundle

完成标准：

- EEG 热态生命周期收口清晰
- 数据库存储保持最小闭环

---

## 15. 给金伟的实施建议

本次实施建议优先级如下：

### P0 必做

1. 去掉 `/live` 绑定 EEG session 的副作用
2. 建立 EEG Redis live 热态
3. 建立 EEG raw file 冷存
4. 建立 EEG window 推理结果落库
5. turn 结束清理 Redis 热态

### P1 可选

1. 为 EEG 同步补 `multimodal_captures`
2. 增加更完整的质量标记
3. 增加 assessment 侧 EEG 流水线测试

### P2 暂缓

1. EEG turn summary
2. EEG key windows
3. EEG finalized bundle
4. EEG 进入 risk-service 统一聚合特征

---

## 16. 最终结论

当前 EEG 的核心问题不是模型，而是接入方式不在系统主链上。

与 `dev` 分支已经做好的 `face / pose` Redis 热链路相比，当前 EEG 缺的不是更多复杂摘要，而是最基本的三件事：

1. 正式的 Redis 实时热态
2. 正式的原始文件冷存
3. 正式的 window 结果落库

因此本次推荐方案不是把 EEG 直接做成视觉那样的 finalized bundle 模态，而是先做成一个更合适的精简闭环：

- 看板看 Redis
- 原始数据看对象存储
- 下游消费 window 推理结果

这是当前最贴合业务目标、最稳、也最容易实施的一版 EEG 接入方案。
