# EEG Current Chain And Gap Analysis

更新时间：2026-06-14

适用对象：金伟

目的：基于当前仓库最新代码，梳理 EEG 在系统中的真实落地链路，并对照 `docs/architecture/eeg-live-preview-stream-refactor-design_20260611.md` 说明当前差距、边界与下一步重点。

本文不修改实现，只做现状澄清与差距分析。

## 1. 任务边界结论

从仓库现有文档看，金伟当前承担的 EEG 相关任务边界是明确的：

- `docs/services/multimodal-service/tasks.md`
  - EEG 模态与脑电帽硬件 owner 是金伟
  - 未完成项包含“EEG 模态接入”
  - P2 明确包含 `MM-22：补充 EEG 对齐统一 Schema`
- `docs/services/risk-service/tasks.md`
  - 风险链路的多模态特征包由刘倩 / 金伟配合提供
- `docs/architecture/eeg-live-preview-stream-refactor-design_20260611.md`
  - 已把下一阶段 EEG 改造目标正式定义为“双链路”
  - 文档末尾明确要求金伟本人复查整条 EEG 链路

一句话概括：

当前你的任务不是“把 EEG 从 0 接进系统”，而是以 EEG owner 身份把已经接入的链路重新收口、澄清边界，并推进到 `2026-06-11` 文档定义的正式双链路形态。

## 2. 当前实现的一句话结论

当前 EEG 已经具备以下主能力：

- Windows 宿主机采集或回放
- Redis Stream 原始传输
- `multimodal-service` 解码
- turn 内 EEG preview 缓冲
- 10 秒窗口推理
- MinIO 原始窗口冷存
- 数据库窗口结果落库
- consultation / assessment 看板展示
- assessment 阶段向 risk 聚合 EEG 特征

但当前仍不是正式双链路，而是：

“后端 runtime 内部已经开始分成 preview 与 inference 两类职责，但对外接口、前端状态和会话生命周期仍耦合在统一 `multimodal_live` 链路中。”

## 3. 当前真实链路

### 3.1 宿主机采集链路

当前 Windows 宿主机侧 EEG 已收口到单入口：

- `tools/eeg-tools`
- `scripts/start_eeg_tools.ps1`
- `bridge`：真实蓝牙设备采集
- `replay`：录制回放或模拟数据

与 `docs/architecture/eeg-pure-docker-single-command-plan_20260607.md` 一致，当前开发链路是：

```text
Windows host
  -> tools/eeg-tools
  -> bridge / replay
  -> Redis Stream

Docker Compose
  -> 唯一一份 multimodal-service
  -> consultation / assessment / risk / gateway
```

关键代码：

- `tools/eeg-tools/bridge-runtime/app/bridge_worker.py`
- `tools/eeg-tools/bridge-runtime/app/redis_stream_writer.py`

当前 Redis Stream entry 中承载的核心字段包括：

- `payload_hex` 或 `payload_base64`
- `device_id`
- `ts`
- `received_at`
- `packet_count`

这部分说明：

- 宿主机只负责采集与写流
- 业务逻辑已固定在 Docker 内
- 这条边界与 `2026-06-11` 目标文档是一致的

### 3.2 `multimodal-service` EEG runtime 链路

EEG 主要实现在：

- `services/multimodal-service/app/services/eeg_runtime.py`
- `services/multimodal-service/app/services/eeg_protocol.py`

数据流如下：

```text
Redis Stream
  -> EEGRedisStreamProvider
  -> EEGPacketDecoder
  -> WavePacket / FeaturePacket
```

其中：

- `WavePacket` 负责三通道波形样本
- `FeaturePacket` 负责特征帧

runtime 内当前已经天然分成两类处理：

1. wave packet
   - 进入 preview buffer
   - 进入 pending live delta
   - 驱动前端波形显示
2. feature packet
   - 进入当前窗口 feature 累计
   - 满足窗口条件后执行推理

也就是说，后端内部其实已经有“预览”和“推理”两种不同职责，只是还没有在外部 contract 上彻底分离。

### 3.3 当前 turn 绑定模型

当前 EEG runtime 使用单个 `_active_binding` 维护活跃上下文：

- 同时只存在一个 active EEG turn binding
- 新 turn 启动时，如果已有旧 binding，会先把旧 binding 以 `rebound` 收尾

当前 binding 信息包括：

- `session_id`
- `turn_id`
- `flow_run_id`
- `stage_id`
- `question_key`
- `preview_buffer`
- `latest_results`
- `pending_live_samples`
- `current_window`

这意味着当前 EEG 生命周期本质上是“绑定 active turn”，不是“绑定 consultation session 的独立 preview 上下文”。

这是当前实现与目标文档之间最重要的结构差异之一。

### 3.4 consultation / assessment 如何驱动 EEG turn

当前 EEG turn 的启动和结束不是 EEG runtime 自主决定，而是由上游服务 best-effort 驱动：

- `services/consultation-service/app/services/consultation_engine.py`
- `services/assessment-service/app/services/assessment_engine.py`

当前行为：

- consultation 在进入 `waiting_user_input` 时会尝试 `start_eeg_turn`
- consultation 提交回答时会 `finish_eeg_turn`
- assessment 在当前题目有效时会尝试 `start_eeg_turn`
- assessment 提交答案时会 `finish_eeg_turn`

更关键的是，当前 `get .../multimodal/live` 与 `.../multimodal/live/stream` 也带有启动 EEG turn 的副作用。

也就是：

- “读 live”
- “建/续 EEG turn 绑定”

这两件事目前还没完全解耦。

### 3.5 预览链路当前是如何对外暴露的

当前 preview 没有独立接口。

现状是：

1. EEG runtime 生成两类 live 数据
   - `eeg_live`
   - `eeg_waves`
2. `multimodal_session_service` 把它们并入统一 `multimodal_live`
3. `multimodal /live` 与 `/live/stream` 一并对外输出
4. consultation-service / gateway-service 只是继续代理这条统一 live 流

当前相关接口：

- `GET /api/v1/multimodal/sessions/{session_id}/live`
- `GET /api/v1/multimodal/sessions/{session_id}/live/stream`
- `GET /api/v1/consultations/{session_id}/multimodal/live`
- `GET /api/v1/consultations/{session_id}/multimodal/live/stream`

当前 SSE 事件名是：

- `live_snapshot`

不是目标文档要求的：

- 独立 EEG preview SSE
- 事件名 `eeg_preview`

### 3.6 当前预览数据模型

当前前端收到的 EEG 数据分成两块：

1. `eeg_live`
   - 低频摘要
   - `device_status`
   - `device_id`
   - `channel_names`
   - `sampling_rate`
   - `latest_result`
   - `latest_results`
   - `error_message`
2. `eeg_waves`
   - 高频波形
   - `samples`
   - `append_samples`
   - `reset`

这说明现在的接口在一个统一 contract 中混合了：

- summary
- preview wave payload

目标文档要求是：

- summary 留在原有 `/live`
- 高频 preview 单独拆流

当前尚未做到。

### 3.7 前端当前如何消费 EEG

前端咨询页核心逻辑在：

- `apps/consultation/client/src/pages/ConsultationPage.tsx`
- `apps/consultation/client/src/lib/useJsonEventStream.ts`
- `apps/consultation/client/src/lib/multimodalLiveMerge.ts`
- `apps/consultation/client/src/components/ConsultationStatusPanel.tsx`

当前机制：

1. 优先走 SSE `live_snapshot`
2. SSE 不活跃时退回 HTTP 轮询
3. 收到 live patch 后 merge 到 `consultation.multimodal_live`
4. EEG 面板从全局 `multimodal_live` 里读取 `eeg_live` / `eeg_waves`
5. 波形绘图组件内部再维护局部 fixed buffer / canvas

当前前端其实已经做了两层处理：

- 上层：全局业务状态 merge
- 下层：EEG 绘图局部缓冲

真正的问题不在 canvas，而在于：

- 高频 EEG 数据源仍然进入 consultation 全局状态
- SSE patch 和 HTTP full snapshot 会在同一 merge 流程中混用

### 3.8 推理 / 冷存 / 落库链路

当前 feature packet 累积到窗口后，会执行完整窗口闭环：

```text
FeaturePacket
  -> current_window.feature_samples
  -> 满足窗口条件
  -> 推理
  -> 原始窗口序列化 npz
  -> MinIO 上传
  -> MultimodalCapture 落库
  -> MultimodalInferenceResult 落库
```

这条链路当前已经是正式主链的一部分，且和目标文档总体一致。

当前窗口结果也会回写到 live state 中，供看板读取最近结果。

### 3.9 assessment / risk 当前如何消费 EEG

当前 EEG 下游消费主要落在 assessment，而不是 consultation。

assessment 当前行为：

1. 提交当前题答案
2. 调用 `finish_eeg_turn`
3. 再调用 `get_eeg_turn_results`
4. 把返回的 `window_results` 记入 `capture_context.eeg_turn_results`
5. 最后汇总成 `eeg_features`
6. 与其他模态一起打包进 risk 输入

相关位置：

- `services/assessment-service/app/services/assessment_engine.py`
- `services/risk-service/app/services/risk_engine.py`

这说明：

- 当前 EEG 已经进入 risk 聚合口径
- 但主要是通过 assessment 侧的 turn results 进入
- consultation 侧目前还没有同等强度的 EEG 特征 handoff

## 4. 当前实现与 `2026-06-11` 目标设计的差距

下面按目标文档逐项对照。

### 4.1 宿主机边界

目标：

- Windows 宿主机只跑 bridge / replay
- Docker 内只有一份 `multimodal-service`

现状：

- 已达到

结论：

- 这一项不是当前阻塞点

### 4.2 原始流主链

目标：

- Redis Stream 原始流保持不变
- 10 秒窗口推理保持不变
- MinIO / DB 落库保持不变

现状：

- 基本已达到

补充注意：

- `services/multimodal-service/app/config.py` 默认 `EEG_WINDOW_SECONDS=10`
- `infra/compose/docker-compose.dev.yml` 也是 `10`
- 但 `services/multimodal-service/.env.example` 仍写的是 `60`

结论：

- 主链能力已具备
- 但配置示例与实际默认值不完全一致，后续应统一口径

### 4.3 预览与推理彻底解耦

目标：

- preview 与 inference 是两条明确链路

现状：

- runtime 内部已经部分分离
- 对外接口仍未分离

具体表现：

- wave / feature 在 runtime 内分开处理
- 但 preview 仍通过 `multimodal_live` 对外发
- summary 和 preview 仍共用一条 `/live` / `/live/stream`

结论：

- 内部分流已有基础
- 外部分流尚未完成

### 4.4 `/live` 只保留低频 EEG summary

目标：

- `/live` 中 EEG 只保留低频字段
- 禁止继续承载高频波形数组

现状：

- 当前 `/live` 仍然带 `eeg_waves`
- 并且 `eeg_waves` 中仍可能出现 `samples` 或 `append_samples/reset`

结论：

- 与目标不一致
- 这是当前最直接的 contract 层差距

### 4.5 独立 EEG preview SSE

目标：

- 新增 EEG preview 专用 SSE
- 建议路径：
  - `GET /api/v1/consultations/{session_id}/multimodal/eeg/preview/stream`
- 事件名固定为 `eeg_preview`

现状：

- 不存在独立 EEG preview SSE
- 只有通用 `live/stream`
- 事件名是 `live_snapshot`

结论：

- 当前完全未达到目标接口形态

### 4.6 preview 生命周期不再绑定单个 turn

目标：

- preview 绑定 consultation session 的可视化上下文
- turn 切换、题目切换、窗口完成都不能重建 preview 会话

现状：

- 数据采集处理依赖 `begin_turn` / `finish_turn`
- runtime 内只有一个 `_active_binding`
- 本质上仍是“active turn 模型”

补充 nuance：

- 当前实现会尝试从上一轮 live payload carryover 最近波形
- 因此不一定每次 turn 切换都硬重置
- 但 preview 是否持续存在，仍取决于 active binding 是否存在、Redis 热态是否还在、进程内缓存是否还在

结论：

- 还没有达到“preview 生命周期独立于 turn”的正式目标

### 4.7 `/live` 读取不应再带副作用

目标：

- 预览链路应独立存在
- 不应通过“读 live”来隐式创建或续命 EEG turn

现状：

- consultation / assessment 的 `get .../multimodal/live`
- `stream .../multimodal/live`
- 在活跃状态下都可能调用 `_start_eeg_turn_best_effort`

结论：

- 当前仍存在明显副作用
- 这与早期差距分析文档中“去掉 `/live` 绑定 EEG session 副作用”的建议一致

### 4.8 前端状态边界

目标：

- EEG 高频 preview 不再进入 `consultation` 全局业务状态
- 波形状态应由面板局部 store 或等价局部状态维护

现状：

- `applyConsultationMultimodalLive` 会把 EEG patch merge 到全局 `consultation.multimodal_live`
- EEG 面板再从全局状态中取出数据

补充：

- 绘图组件内部已经做了局部 fixed buffer，这是好基础
- 但数据源入口仍然是全局 consultation state

结论：

- 当前只完成了“局部绘图优化”
- 没完成“高频状态源从全局业务状态中移出”

### 4.9 SSE patch 与 HTTP full snapshot 混用

目标：

- preview 流应是单一、可丢弃、单调递增的 chunk 流

现状：

- SSE 用 `live_snapshot`
- HTTP fallback 用 `/live`
- 前端统一用 `mergeConsultationMultimodalLive`
- merge 中同时兼容 `samples` 与 `append_samples/reset`

结果：

- 一条 merge 逻辑要同时处理
  - full snapshot
  - delta patch
  - SSE
  - HTTP fallback

结论：

- 这正是 `2026-06-11` 文档指出的当前结构性问题

### 4.10 preview reset 语义

目标：

- reset 只能由重连、会话重建、通道变更、采样率变更、手动清空触发

现状：

- 当前 `live_stream_reset_pending` 主要在新 binding 且没有 carryover preview 时触发
- 也就是说 reset 语义更多来自“有没有 carryover”
- 不是显式的链路级 reason contract

结论：

- 当前 reset 机制不够正式
- 缺少目标文档要求的“带原因、可审计”的 reset 语义

### 4.11 preview 事件契约

目标：

- 单事件只发增量 chunk
- 始终显式带 `sampling_rate`、`channel_names`
- 有 `chunk_seq_start`、`chunk_seq_end`
- 同一会话 seq 单调递增

现状：

- 当前 wave delta 中已有 `append_samples`
- 样本里也有 `seq`
- 但没有独立的 `eeg_preview` 事件 contract
- 没有正式对外暴露 `chunk_seq_start` / `chunk_seq_end`
- 没有独立 preview 流的单调递增契约说明

结论：

- 有部分素材
- 但正式 contract 还没建立

### 4.12 多会话 / 并发结构

目标文档没有显式展开这一点，但从正式双链路设计出发，preview 应是按会话隔离的。

现状：

- `EEGRuntimeService` 当前只有一个 `_active_binding`
- 新 binding 会把旧 binding 收尾

这意味着：

- 当前实现天然更接近“单设备 / 单活跃会话”
- 如果未来存在多 session 并行 EEG，需要重新设计 runtime 绑定模型

结论：

- 这是当前实现的重要结构前提
- 不是立刻要改的点，但必须在后续设计中明确承认

## 5. 当前最重要的事实判断

### 5.1 已经具备的基础

以下基础现在已经有了，不需要推倒重来：

- Windows 宿主机单入口
- Redis Stream 原始传输
- BLE / replay 到 Stream 的稳定桥接
- EEG 协议解码
- wave / feature 内部分流
- 10 秒窗口推理
- MinIO 冷存
- 数据库落库
- assessment 侧 EEG 特征进入 risk 聚合
- 前端绘图组件内部局部 buffer 能力

### 5.2 当前真正卡住的点

真正卡住的不是模型，也不是原始流，而是以下五件事：

1. preview 对外仍挂在统一 `multimodal_live`
2. `/live` 读取仍带 EEG turn 启动副作用
3. preview 生命周期仍依赖 active turn
4. 前端高频 EEG 数据仍进入 consultation 全局状态
5. SSE patch 与 HTTP full snapshot 混用同一 merge 模型

### 5.3 现状最准确的描述

当前系统不是“完全单链路”。

更准确地说：

- 后端内部已经开始做双职责
- 但接口层、状态层、生命周期层仍是单链路心智

所以这次改造更适合定义为：

“把已经半分流的 EEG runtime，继续推进成外部 contract、生命周期和前端状态都一致的正式双链路。”

## 6. 建议的下一步重点

如果后续按 `docs/architecture/eeg-live-preview-stream-refactor-design_20260611.md` 推进，建议优先级如下：

### P0

1. 去掉 consultation / assessment `live` 读取对 `start_eeg_turn` 的副作用
2. 把 EEG 高频 preview 从统一 `multimodal_live` contract 中拆出去
3. 新增独立 EEG preview SSE
4. 前端把 EEG 高频状态从 consultation 全局状态中移出
5. 明确 reset reason 与 preview 生命周期

### P1

1. 把 preview 生命周期从 active turn 绑定迁移到 session 级可视化上下文
2. 统一 preview event contract
3. 对 SSE 中断、HTTP fallback、重连后的 carryover 语义做专门收口

### P2

1. 进一步评估 `_active_binding` 的单实例模型是否满足未来并发场景
2. 补齐更多集成测试与异常恢复测试
3. 统一 EEG 相关环境变量文档与示例值

## 7. 最终结论

当前 EEG 主链已经不是空白，真正的问题也不是“采集不到”或“推理没接入”。

当前最核心的结构性问题是：

- 高频 preview 和低频 summary 还没有在对外 contract 上彻底拆开
- preview 生命周期还没有从 turn 语义中抽离
- 前端仍把 EEG 高频流当作 consultation 全局业务状态的一部分来消费

因此，`docs/architecture/eeg-live-preview-stream-refactor-design_20260611.md` 的方向判断是对的。

下一阶段不应继续在当前 `multimodal_live` 上修补波形刷新，而应正式推进：

- 完整推理主链保持稳定
- 可丢弃实时预览链路独立成型
- 前端局部 ring buffer + canvas 独立消费 preview SSE

这才是当前代码状态下最顺、风险最低、也最符合后续 Jetson / Docker 演进方向的改法。
