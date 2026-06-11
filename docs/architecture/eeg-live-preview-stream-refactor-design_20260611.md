# EEG 实时波形预览双链路改造设计

更新时间：2026-06-11

适用范围：`Windows + Docker` 当前开发链路，以及后续 `Jetson + Docker` 部署链路中的 EEG 预览与推理集成

关联文档：

- [EEG 单入口与纯业务容器边界](/e:/DataSets/Projects/depression-system/docs/architecture/eeg-pure-docker-single-command-plan_20260607.md)
- [EEG 现状问题、标准差距与 Redis 热链路接入方案](/e:/DataSets/Projects/depression-system/docs/multiEmo/eeg-gap-analysis-and-refactor-plan_20260602.md)

## 1. 文档目标

本文档定义 EEG 接入系统后的下一阶段正式改造目标：

1. 前端 EEG 波形图必须连续、平滑、可持续滚动显示。
2. 波形图不能在答题提交、题目切换、窗口推理完成时闪烁、消失或整段重置。
3. EEG 实时预览链路与 EEG 推理/入库链路必须彻底解耦。
4. 不允许为了前端绘图需求破坏现有 Redis Stream 原始采集、10 秒窗口推理、MinIO 冷存和数据库落库逻辑。

本文档是给实现人员的正式设计说明，不是讨论稿。

## 2. 当前问题定义

当前 EEG 已经成功接入系统，但前端实时显示存在结构性问题：

1. EEG 波形高频更新被并入 `consultation.multimodal_live` 这类页面级业务状态。
2. 波形数据既混用 full snapshot，又混用 `append_samples/reset` 增量 patch。
3. SSE 短暂抖动时会退回轮询，波形状态容易出现全量回填和局部重置混杂。
4. 题目切换、语音提交、turn 切换、EEG 窗口推理完成时，前端波形可能出现短时空白、闪断、重新挂载或整块卡顿。
5. 前端当前对 EEG 波形的“实时显示需求”和后端对 EEG 原始流的“完整推理需求”没有边界，导致一条状态链路承担了两种不同目标。

这说明当前主要问题不是“采集不到 EEG”，而是“把高频流媒体预览错误地建模成了页面业务状态的一部分”。

## 3. 本次改造的正式目标

本次改造完成后，系统必须达到以下目标：

1. EEG 原始数据仍按现有方式进入 Redis Stream，并继续被 `multimodal-service` 完整消费。
2. EEG 推理仍按固定窗口执行，当前默认窗口仍为 `10s`。
3. EEG 原始窗口文件仍写入 MinIO，当前 `.npz` 格式和对象路径语义不改。
4. EEG 窗口级推理结果仍写入 `multimodal_inference_results`，窗口采集元数据仍写入 `multimodal_captures`。
5. 前端实时波形改为只消费一条“可丢弃的预览流”，只保留最近几秒数据，不再依赖全量历史回放。
6. 前端 EEG 波形绘制与咨询页面全局状态彻底解耦，EEG 高频更新不能再拖动整页频繁重渲染。

## 4. 非目标

本次改造明确不做以下事情：

1. 不重写 EEG 蓝牙采集协议。
2. 不重写 Redis Stream 原始传输格式。
3. 不改 EEG 模型、不改特征工程、不改窗口推理算法。
4. 不把完整 EEG 原始波形写入数据库。
5. 不把前端预览用的短时波形缓存持久化到数据库或对象存储。
6. 不在本次改造中顺带重构非 EEG 的 face / pose / speech / text 实时链路。

## 5. 冻结边界与禁改项

以下边界在本次改造中视为冻结，未经单独设计评审不得修改。

### 5.1 宿主机采集与 Docker 业务边界冻结

必须保留：

- Windows 宿主机 `eeg-bridge.exe` 或统一 EEG 工具负责蓝牙采集
- Redis Stream 作为 EEG 原始传输总线
- Docker 内唯一一份 `multimodal-service` 负责业务消费、推理、热态输出、冷存和落库

绝对不允许：

- 恢复“宿主机另起完整 multimodal-service”的旧链路
- 前端浏览器直连宿主机蓝牙采集进程
- 为了波形预览临时再起一套独立 EEG 业务服务

### 5.2 原始数据与推理持久化边界冻结

必须保留：

- 原始采集仍走 Redis Stream
- 原始窗口文件仍按窗口切片冷存到 MinIO
- 推理结果仍按窗口落标准表

绝对不允许：

- 为了前端显示把全量原始波形写入数据库
- 为了前端显示把每 `80~120ms` 的预览 chunk 写入 MinIO
- 为了前端显示改变窗口级落库表结构的主语义

### 5.3 前端状态边界冻结

必须做到：

- EEG 高频预览状态不再进入 `consultation` 全局业务状态
- EEG 实时波形必须由面板局部 store 或等价局部状态树维护

绝对不允许：

- 继续把 EEG 高频 `samples` / `append_samples` 并入 `consultation.multimodal_live`
- 继续让 EEG 波形更新触发咨询页面主体区域一起重渲染
- 继续让“面板开关状态”直接决定 EEG 预览链路是否存在

### 5.4 reset 语义冻结

允许触发 EEG 预览 reset 的场景仅限：

1. 设备重新连接
2. 会话真正重建
3. EEG 通道数变化
4. EEG 采样率变化
5. 用户显式手动清空预览

绝对不允许触发 EEG 预览 reset 的场景：

1. 提交一次录音
2. 题目切换
3. turn 开始
4. turn 结束
5. 10 秒推理窗口完成
6. `latest_result` 更新

## 6. 目标架构

本次改造后的 EEG 正式架构必须拆成两条逻辑链路。

### 6.1 推理主链路

```text
EEG 设备
  -> Windows 宿主机 bridge
  -> Redis Stream 原始流
  -> multimodal-service 解码
  -> 波形样本累计 / 特征帧累计
  -> 10 秒窗口推理
  -> 原始窗口写 MinIO
  -> 窗口结果写数据库
```

这条链路目标是：完整、可靠、可追溯、可恢复、可用于下游分析。

### 6.2 预览链路

```text
EEG 设备
  -> Windows 宿主机 bridge
  -> Redis Stream 原始流
  -> multimodal-service 解码
  -> EEG preview chunk 输出
  -> consultation-service / gateway 对外提供 SSE
  -> 前端 EEG 局部 ring buffer
  -> canvas 持续滚动绘制
```

这条链路目标是：低延迟、可丢弃旧数据、稳定、流畅。

### 6.3 两条链路的职责分工

推理主链路负责：

- 完整消费原始流
- 形成窗口
- 执行推理
- 冷存
- 落库

预览链路负责：

- 向前端发送最近一小段增量波形
- 只保留短时可视化所需数据
- 不承担完整历史保存责任

## 7. 接口与数据契约设计

### 7.1 现有 consultation live summary 继续保留

当前 consultation / assessment 侧面向页面的“多模态摘要”接口继续保留，但 EEG 部分只保留低频摘要字段：

- `device_status`
- `device_id`
- `channel_names`
- `sampling_rate`
- `latest_result`
- `latest_results`
- `error_message`
- `updated_at`

禁止继续在该 summary 中承载高频波形大数组。

### 7.2 新增 EEG preview 专用 SSE 接口

建议新增统一外部接口：

- `GET /api/v1/consultations/{session_id}/multimodal/eeg/preview/stream`

内部实现方式可以是：

1. consultation-service 代理 multimodal-service 的 EEG preview 事件流
2. gateway-service 对外统一暴露

前端不应直接跨过 consultation-service 去访问宿主机或内部采集源。

### 7.3 EEG preview 事件结构

正式事件名建议固定为：

- `eeg_preview`

事件载荷建议如下：

```json
{
  "session_id": "consultation-session-id",
  "multimodal_session_id": "multimodal-session-id",
  "updated_at": "2026-06-11T12:00:00Z",
  "device_status": "streaming",
  "device_id": "FC:91:66:E5:55:97",
  "sampling_rate": 500,
  "channel_names": ["T7", "T8", "Fpz"],
  "reset": false,
  "chunk_seq_start": 120000,
  "chunk_seq_end": 120049,
  "samples": [
    {
      "seq": 120000,
      "captured_at": "2026-06-11T12:00:00.080Z",
      "values": [1.2, -0.4, 3.8]
    },
    {
      "seq": 120001,
      "captured_at": "2026-06-11T12:00:00.082Z",
      "values": [1.1, -0.3, 3.6]
    }
  ]
}
```

### 7.4 预览事件契约要求

必须满足：

1. 单个事件只包含增量 chunk，不返回完整历史波形。
2. `reset=false` 时表示对当前 ring buffer 追加。
3. `reset=true` 时必须伴随明确的链路级原因，例如重连或采样参数变更。
4. `sampling_rate` 与 `channel_names` 必须始终显式携带，避免前端状态漂移。
5. 同一会话的 EEG preview 必须按 seq 单调递增。

## 8. 后端改造要求

### 8.1 `multimodal-service` 的改造要求

实现人员需要在 `multimodal-service` 内完成以下改造：

1. 保留现有 `EEGRuntimeService` 对原始流的完整消费能力。
2. 在 EEG runtime 内新增 preview chunk 构造逻辑。
3. preview 输出周期与推理窗口周期彻底解耦。
4. preview 输出只取最近一个短时间片内的新样本。
5. 预览通道不能影响窗口级推理累计。

### 8.2 preview 输出频率

推荐值：

- `80ms` 到 `100ms` 一次

理由：

- `500Hz` 采样下，`100ms` 约对应 `50` 个点/通道，足够平滑
- 事件数显著低于逐样本推送
- 对前端和 SSE 都更稳

禁止：

- 逐样本单条推送
- 每次都发送最近 4 秒全量波形

### 8.3 preview 生命周期要求

preview 生命周期必须绑定到“咨询会话的 EEG 可视化上下文”，而不是绑定到单个 turn。

必须做到：

- turn 切换不重建 preview 会话
- 推理窗口完成不重建 preview 会话
- 题目切换不重建 preview 会话

可以在以下情况重建：

- consultation session 真正结束
- multimodal session 真正重建
- 设备硬重连

### 8.4 summary 与 preview 分流

后端必须把 EEG 输出拆成两类：

1. `summary`
   - 低频
   - 给页面其他区域和结果卡片使用
2. `preview`
   - 高频
   - 只给波形画布使用

绝对不允许再使用一套 payload 同时承担这两个职责。

## 9. 前端改造要求

### 9.1 总体原则

前端必须把 EEG 波形视为“流媒体画布数据”，而不是“咨询页面全局 store 的字段”。

### 9.2 局部 store 设计

前端 EEG 面板内部应维护局部 store，至少包含：

- `connected`
- `deviceStatus`
- `deviceId`
- `samplingRate`
- `channelNames`
- `lastSeq`
- `lastChunkAt`
- 每个通道各自的 ring buffer

建议 ring buffer 长度：

- 最近 `4~6s`

在 `500Hz` 采样下：

- `4s` 约为每通道 `2000` 点
- `6s` 约为每通道 `3000` 点

### 9.3 数据保留策略

前端 EEG 预览数据允许“用完就丢”。

必须做到：

- append 新样本时超出上限就丢掉最旧样本
- 不尝试在前端保存完整会话历史波形
- 不为了支持重新打开面板而保留无限长数组

### 9.4 绘制策略

必须使用：

- `requestAnimationFrame`
- canvas 或等价连续绘图方案

推荐策略：

1. SSE 每 `80~100ms` 收到一批样本
2. 样本先进入 ring buffer
3. 绘制层按浏览器帧率持续滚动
4. 滚动偏移由时间驱动，而不是完全依赖 React 重渲染触发

绝对不允许：

- 每来一批样本就重建整棵页面组件树
- 依赖全局状态 merge 后再驱动画布
- 依赖 HTTP 轮询作为正常波形主来源

### 9.5 面板开关与订阅生命周期

前端必须把“是否显示面板”和“是否维持 EEG 预览链路”分开。

正式要求：

1. 进入咨询页面后，EEG preview 订阅应绑定到页面级生命周期，而不是绑定到面板展开状态。
2. 面板收起后可以暂停重绘，但不能因此清空 EEG buffer。
3. 面板再次展开时，应立即显示最近几秒连续波形，而不是重新从空白开始。

### 9.6 UI 结构要求

右侧 EEG 显示区建议拆成两个子区域：

1. `EegWaveCanvasPanel`
   - 高频更新
   - 只关心波形、设备状态、采样参数
2. `EegInferenceSummaryCard`
   - 低频更新
   - 只关心最新窗口结果、top3、设备摘要

目的：

- 推理结果更新不能带着波形画布一起大规模重渲染

## 10. 明确禁止的实现方式

以下实现方式本次明确禁止：

1. 继续往 `consultation.multimodal_live.eeg_waves` 塞高频波形数组
2. 继续依赖 `append_samples + reset + full samples` 混用作为长期正式协议
3. 继续把 SSE 中断后的 `1s` 轮询当作正常波形主链路
4. 在题目切换或提交答案时清空前端波形缓存
5. 为了图省事把 EEG 预览直接持久化进数据库
6. 直接让浏览器访问宿主机采集服务
7. 在前端保留完整会话全量 EEG 历史数组

## 11. 分步实施方案

### Step 0：冻结边界并打标

要做的事：

1. 由实现人员确认当前线上/开发分支中 EEG 原始链路仍是：
   `bridge -> Redis Stream -> multimodal-service`
2. 给现有 consultation live summary 与 EEG preview 相关代码加设计注释或任务标记，明确 summary 不再承担高频波形职责。
3. 记录当前窗口推理、MinIO 落冷存、DB 落库行为，作为回归基线。

绝对不允许更改：

- Redis Stream 原始采集协议
- 10 秒窗口推理逻辑
- 数据库落库表

验收标准：

1. 有一份冻结边界确认记录
2. 能明确列出改造前后哪些链路不能碰

### Step 1：后端拆出 EEG preview 专用通道

要做的事：

1. 在 `multimodal-service` 内新增 EEG preview 事件模型。
2. 从 runtime 中输出固定节奏的 preview chunk。
3. 保持推理主链路逻辑不变。

绝对不允许更改：

- MinIO `.npz` 冷存格式
- 窗口推理的结果表写入逻辑

验收标准：

1. 同一会话能连续收到 `80~100ms` 一批的 EEG preview 事件
2. preview 事件只包含增量样本，不包含整段历史样本
3. 窗口推理和 preview 可以同时工作，互不阻塞

### Step 2：consultation-service / gateway 对外暴露 preview SSE

要做的事：

1. 新增 consultation 侧 EEG preview 外部 SSE 接口。
2. 将内部 multimodal preview 事件映射为前端可稳定消费的 consultation 级接口。

绝对不允许更改：

- 前端直接跨过 consultation-service 去连宿主机或内部采集源

验收标准：

1. 浏览器能通过 consultation 域下的正式接口收到连续 EEG preview
2. 接口断开重连后不会把旧 preview 历史整段重放为 full snapshot

### Step 3：前端实现 EEG 局部 ring buffer store

要做的事：

1. 在 EEG 面板内部新增局部 store。
2. 把 preview SSE 直接写入 ring buffer。
3. 设置固定最大长度，只保留最近 `4~6s`。

绝对不允许更改：

- 把 ring buffer 再包装回 consultation 全局业务状态

验收标准：

1. 连续运行至少 `5min`，前端内存不随时间无上限增长
2. 面板内任何时刻只保留最近短时波形数据

### Step 4：前端改为连续绘图模型

要做的事：

1. 使用 `requestAnimationFrame` 连续滚动绘制波形。
2. 绘制层从 ring buffer 读取数据，不再依赖 React 频繁重渲染来推进画面。
3. 把 EEG 波形组件与结果摘要组件拆开。

绝对不允许更改：

- 继续让波形更新导致咨询页主体一起抖动

验收标准：

1. 波形可连续滚动，不再出现每隔 `1~2s` 整块消失一次
2. 提交录音时页面主区域不卡顿、不白屏
3. 波形刷新不再拖动视频区、字幕区、按钮区频繁重渲染

### Step 5：清理旧 EEG 高频状态依赖

要做的事：

1. 从 consultation 全局状态中移除 EEG 高频波形依赖。
2. 保留 EEG 低频摘要字段供结果卡片显示。
3. 清理旧的 full snapshot / append / reset 混合路径中的废弃逻辑。

绝对不允许更改：

- 删除窗口级结果摘要字段
- 删除设备状态字段

验收标准：

1. consultation 全局状态中不再承载高频 EEG 波形数组
2. 右侧 EEG 摘要仍能显示设备状态与最新结果

### Step 6：全链路联调与回归

要做的事：

1. 使用真实 EEG 设备连续运行完整咨询流程。
2. 覆盖以下场景：
   - 面板展开/收起
   - 录音开始/结束/提交
   - 题目切换
   - 推理窗口完成
   - SSE 短暂重连
3. 验证前端流畅度与后端落库正确性。

绝对不允许更改：

- 因为联调追求“看起来顺”而牺牲原始流完整消费

验收标准：

1. 前端波形在完整咨询流程中保持连续
2. `.npz` 原始窗口文件仍正常生成
3. `multimodal_captures` 和 `multimodal_inference_results` 仍按窗口正常写入
4. 不出现“为了预览稳定，推理结果反而异常”的回归

## 12. 每一步的测试要求

### 12.1 后端测试

至少覆盖：

1. preview chunk 生成逻辑单测
2. reset 触发条件单测
3. turn 切换不触发 reset 的单测
4. 窗口推理完成不触发 preview reset 的单测
5. preview 与窗口推理并行时的回归测试

### 12.2 前端测试

至少覆盖：

1. ring buffer 上限控制
2. append 后旧数据淘汰逻辑
3. 面板收起再展开仍能立即恢复最近波形
4. 结果摘要更新不触发波形组件重建
5. 波形组件卸载/重挂时不会污染全局 consultation 状态

### 12.3 人工联调测试

至少覆盖：

1. 真机连续采样 `10min`
2. 完整问诊流程跑通
3. 重复提交多轮语音
4. 多次展开/收起右侧面板
5. 观察是否还有肉眼可见的闪断、空窗、整块重置、明显卡顿

## 13. 最终完成标准

只有同时满足以下条件，才视为本次改造完成：

1. EEG 波形能在咨询页面中连续、平滑、稳定滚动显示。
2. 波形在答题提交、题目切换、10 秒窗口完成时不会闪断。
3. EEG 高频预览不再进入 consultation 全局业务状态。
4. 前端预览数据只保留最近短时波形，用完即丢。
5. 后端原始流消费、窗口推理、MinIO 冷存、数据库落库全部维持正确。
6. 没有引入“宿主机完整 multimodal-service”回退方案。
7. Windows 当前开发模式和后续 Jetson 容器化模式都能沿用同一套双链路设计。

## 14. 一句话结论

本次 EEG 改造的正式方向不是“继续在 consultation 全局状态里修补波形刷新”，而是：

把 EEG 分成“完整推理主链路”和“可丢弃的实时预览链路”两套职责边界，用局部 ring buffer + 连续绘图解决前端流畅性，同时保持后端推理和落库链路完全稳定。

## 15. 收尾质量要求

在实现人员完成本次改造、完成联调、并确认满足本文档所有分步验收标准与最终完成标准之后，还必须追加执行一轮收尾质量检查。

### 15.1 必做事项

实现人员必须：

1. 由金伟本人基于当前最新代码再次完整检查 EEG 在系统中的整条链路。
2. 使用 Codex 对 EEG 相关链路做一次面向真实集成的二次审查，重点检查：
   - 采集链路
   - Redis Stream 传输链路
   - `multimodal-service` EEG runtime
   - preview SSE 输出
   - 前端波形显示
   - 窗口推理与落库
   - turn / session 生命周期边界
   - 配置、异常恢复、重连、资源释放、性能和潜在竞态
3. 对 Codex 检查出的 bug、问题或隐患逐项判断并修复。

### 15.2 修复要求

修复阶段必须遵守：

1. 非必要不破坏其他已经写好的链路和代码。
2. 非必要不扩大改动面，不借机重写与本次 EEG 目标无关的模块。
3. 如果发现问题只影响 EEG 局部链路，应优先做局部修复，而不是把 consultation、assessment、gateway 或其他非 EEG 模块整体翻新。
4. 如果某个问题的修复可能影响现有稳定链路，必须先补充影响说明、边界说明和回归验证方案，再实施改动。

### 15.3 最终交付标准补充

只有在以下条件同时满足时，本次 EEG 改造才算真正结束：

1. 本文档前述所有实施步骤已完成。
2. 本文档前述所有验收标准已满足。
3. 金伟本人已完成一轮基于 Codex 的 EEG 链路复查。
4. 复查发现的问题、bug 或隐患已完成必要修复。
5. 修复后未引入对其他已稳定链路的非必要破坏。
