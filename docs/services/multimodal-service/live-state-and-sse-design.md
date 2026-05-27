# `multimodal-service` live 状态与 SSE 实时推送设计与完成说明

更新时间：2026-05-27

适用仓库：`depression-system`

---

## 1. 文档目标

本文档用于说明 `multimodal-service` 与问诊看板的 live 数据设计，以及当前落地结果。

本次改造主要解决了两个问题：

- `consultation-service` 对 live 快照的重复落库
- 当前 HTTP polling 方案的实时性与资源效率不足

本文档当前状态为：

- 设计已落地
- 主链路已完成
- 可作为现状说明使用

---

## 2. 结论摘要

本次改造的核心结论如下：

1. `consultation-service.consultation_sessions.multimodal_live_payload` 已从实现中移除。
2. live 快照已被定义为“热状态”，只服务实时看板，不作为 `consultation-service` 的业务事实持久化。
3. 业务事实继续由各模态自己的明细表、推理结果表、turn bundle 表承担。
4. 实时看板已从“5s polling 主导”演进为“SSE 优先 + polling 降级”。
5. `multimodal-service`、`consultation-service`、`gateway-service`、前端问诊页的 SSE 主链路已接通。

---

## 3. 当前现状

## 3.1 当前前端刷新方式

当前问诊页存在两套并行机制：

- 视觉采样上传间隔：`1500ms`
- live 轮询兜底间隔：`5000ms`

当前行为是：

- 前端每 `1.5s` 抓取一帧视觉输入并上传
- 页面初始化先请求一次 `/consultations/{session_id}/multimodal/live`
- 然后优先建立 `/consultations/{session_id}/multimodal/live/stream`
- 只有 SSE 不可用或中断时，才退回 `5s` polling

当前没有接入 WebSocket。

当前已正式接入：

- SSE

因此系统整体已经变成：

- **SSE 主导，HTTP polling 兜底**

## 3.2 当前 live 读取链路

当前 snapshot 读取链路为：

1. 前端请求 `GET /api/v1/consultations/{session_id}/multimodal/live`
2. `gateway-service` 转发到 `consultation-service`
3. `consultation-service` 调用上游 `multimodal-service /sessions/{session_id}/live`
4. `consultation-service` 直接把 live 数据返回前端

当前 `consultation-service` 在 live 读取时只承担：

- 透传读取

当前 SSE 读取链路为：

1. 前端订阅 `GET /api/v1/consultations/{session_id}/multimodal/live/stream`
2. `gateway-service` 代理到 `consultation-service`
3. `consultation-service` 通过会话绑定关系映射到 `multimodal_session_id`
4. `consultation-service` 代理到 `multimodal-service /sessions/{session_id}/live/stream`
5. `multimodal-service` 通过 Redis pubsub + snapshot reconcile 持续推送 `live_snapshot`

## 3.3 当前 live 数据的真实来源

当前 live 的真实来源并不在 `consultation-service`。

真实数据来源在 `multimodal-service`，而且已经存在热态分层：

- `speech` / `text` 当前状态主要来自 `multimodal_sessions.live_state_payload`
- `face` / `pose` 当前状态优先叠加 Redis 中的 `visual live payload`

这说明当前系统实际上已经在朝下面这个方向演进：

- 业务事实落库
- 看板热态单独维护

只是这条原则还没有彻底贯彻到 `consultation-service`。

## 3.4 当前实现里哪些数据属于业务事实

以下数据属于应当持久化的业务事实：

- `multimodal_visual_frames`
- `multimodal_captures`
- `multimodal_inference_results`
- `multimodal_audio_turns`
- `multimodal_turn_bundles`

这些数据具备以下特征：

- 可追溯
- 可复盘
- 可被下游消费
- 可作为正式审计与诊断依据

## 3.5 当前实现里哪些数据不属于业务事实

以下数据更适合被定义为热状态：

- “此刻 face 主标签是什么”
- “此刻 pose 主标签是什么”
- “当前 speech/text 最新结果是什么”
- “看板右侧当前应该展示什么”

这些数据具备以下特征：

- 时效性强
- 更新频繁
- 很快过期
- 不适合作为主业务事实长期保留

因此，live 快照更适合定义为：

- **看一下就丢的展示态**

而不是正式持久化事实。

---

## 4. 当前问题

## 4.1 问题一：`consultation-service` live 冗余落库

当前 `consultation_sessions.multimodal_live_payload` 的主要问题是：

### 4.1.1 它不是事实源

这份字段只是把上游 `multimodal-service` 的 live 数据复制一份到本地数据库。

它既不是首要来源，也不是最终聚合来源，更不是下游正式消费来源。

### 4.1.2 它带来写放大

轮询一次就会产生一次数据库更新。

如果按照当前 `5s` 轮询估算，一场 `30` 分钟问诊会带来大约：

- `360` 次 `UPDATE consultation_sessions`

而这些更新写入的只是高频变化的 JSON 快照，不是正式业务事实。

### 4.1.3 它放大了 polling 的成本

本来 polling 的代价只是：

- 一次网关转发
- 一次 live 查询

现在又额外变成：

- 一次 consultation-service 数据库写入
- 一次 WAL / MVCC / 行版本膨胀

### 4.1.4 它让职责边界变模糊

`consultation-service` 的职责本应是：

- 问诊状态机
- 会话推进
- 与多模态服务做边界清晰的协作

但 live 缓存落库让它开始承担：

- 上游热状态镜像缓存

这会模糊：

- 会话事实
- 展示热态

之间的界限。

## 4.2 问题二：当前 polling 不是实时推送

即使当前页面通过视觉上传响应做了一部分本地状态补丁，系统主机制仍然是 polling。

这会带来几个问题：

### 4.2.1 独立看板仍然受轮询周期限制

如果是旁路观察页、远端看板、后续运营端看板，通常不会参与本地视觉上传回填，只能依赖 `/live` 拉取。

这类页面会明显感知到：

- 更新不是实时
- 看板有滞后

### 4.2.2 speech / text 的补齐更依赖轮询

视觉链路因为“上传响应即回填”，体感会稍好。

但 `speech` / `text` 的最终完成更依赖：

- 异步任务完成后再次读取 live

这部分更适合被服务端主动推送。

### 4.2.3 无变化时仍然重复请求

即使 live 状态没有变化，前端仍然会定时发送请求。

这会造成：

- 无效 HTTP 请求
- 无效网关转发
- 无效上游查询

如果继续保留 consultation-service 落库，还会造成：

- 无效数据库写入

---

## 5. 设计目标

本次设计目标不是重写整套多模态系统，而是收敛 live 状态与实时推送链路。

## 5.1 目标一：明确数据分层

把数据分成两类：

### 5.1.1 业务事实层

保留正式持久化：

- 原始采样元数据
- 推理结果
- turn 级聚合结果

### 5.1.2 热状态层

只维护短时可展示状态：

- 当前最新 live 看板内容
- 最新更新时间
- 当前模态状态

## 5.2 目标二：去掉 consultation-service 的重复缓存落库

`consultation-service` 应只承担：

- 会话绑定
- 权限校验
- 请求转发

而不再承担：

- live 镜像持久化

## 5.3 目标三：引入单向实时推送

看板读取推荐从 polling 逐步演进为：

- **SSE 优先**
- **polling 降级**

## 5.4 目标四：保持现有接口兼容

在演进期间继续保留：

- `GET /api/v1/multimodal/sessions/{session_id}/live`
- `GET /api/v1/consultations/{session_id}/multimodal/live`

这样可以保证：

- 老页面不被立即打断
- SSE 上线后仍有回退路径

---

## 6. 为什么推荐 SSE 而不是 WebSocket

## 6.1 当前需求是典型单向推送

当前实时看板的主要诉求是：

- 服务端有新的 live 结果时推给前端

而不是：

- 浏览器和服务端频繁双向交互

这类场景更适合：

- SSE

## 6.2 SSE 的工程复杂度更低

相较于 WebSocket，SSE 的优势是：

- 基于 HTTP，接入更直观
- 浏览器原生 `EventSource`
- 自动重连机制更简单
- 更适合“服务端持续发事件，前端被动接收”的模式

## 6.3 更符合当前网关形态

当前项目的网关与服务路由都以 HTTP 为主。

对现有系统而言，先引入：

- SSE 流式代理

要比直接引入完整的：

- WebSocket 连接管理
- 连接状态维护
- 双向消息协议

更容易控制复杂度。

## 6.4 何时才需要 WebSocket

只有在未来明确出现下面需求时，再考虑 WebSocket：

- 客户端需要频繁反向发送控制消息
- 同一连接上需要多种指令双向交互
- 需要更复杂的房间、订阅、广播机制

在当前阶段，这些都不是必须条件。

---

## 7. 当前架构

## 7.1 总体结构

当前架构如下：

1. 各模态处理链路继续生成正式业务事实
2. `multimodal-service` 维护会话级 live 热状态
3. live 热状态变化时，发布 SSE 事件
4. `gateway-service` 提供流式代理
5. 前端优先订阅 SSE
6. SSE 失败时退回 HTTP polling

## 7.2 consultation-service 的当前职责

`consultation-service` 保留：

- `consultation_session_id -> multimodal_session_id` 绑定关系
- 会话所有权校验
- `/consultations/{id}/multimodal/live` 透传读取

`consultation-service` 移除：

- `multimodal_live_payload`
- `multimodal_live_updated_at`
- `_refresh_multimodal_live_snapshot()` 中的持久化副作用

## 7.3 multimodal-service 的当前职责

`multimodal-service` 负责：

- 聚合最新 live 状态
- 维护热状态存储
- 在状态变化时推送事件
- 对外提供：
  - snapshot 读取接口
  - SSE 订阅接口

## 7.4 热状态存储现状

推荐继续把 live 定位为热状态，而不是正式业务事实表。

建议口径：

- `speech/text` live 逐步从 PG 会话字段演进到统一热状态存储
- `face/pose` 继续使用已有 Redis 热态能力
- 会话级统一输出仍然由 `multimodal-service` 拼装

注意：

- 第一阶段不要求把 `multimodal_sessions.live_state_payload` 立即完全移除
- 第一阶段只要求移除 `consultation-service` 的重复镜像落库

---

## 8. 接口设计

## 8.1 保留的 snapshot 接口

继续保留：

- `GET /api/v1/multimodal/sessions/{session_id}/live`

用途：

- SSE 首次连接前初始化
- SSE 断开时降级拉取
- 测试与联调

返回结构保持不变：

- `session_id`
- `updated_at`
- `speech`
- `text`
- `face`
- `pose`

## 8.2 新增的 SSE 接口

当前已提供：

- `GET /api/v1/multimodal/sessions/{session_id}/live/stream`

响应类型：

- `text/event-stream`

当前事件类型：

- `live_snapshot`
- `heartbeat`

## 8.3 `live_snapshot` 事件结构

建议事件 payload 与 snapshot 接口返回尽量一致：

```json
{
  "session_id": "mm-session-1",
  "updated_at": "2026-05-27T10:15:23Z",
  "speech": {},
  "text": {},
  "face": {},
  "pose": {}
}
```

这样可以保证：

- 前端只维护一套 live 解析逻辑

## 8.4 heartbeat 事件

建议周期性发送：

- `heartbeat`

用途：

- 保持连接活性
- 帮助前端感知流是否中断

heartbeat 不要求携带完整 live 数据。

## 8.5 gateway-service 代理接口

当前对前端暴露：

- `GET /api/v1/consultations/{session_id}/multimodal/live/stream`

网关或 consultation-service 可以二选一承担会话映射：

### 方案 A

- 前端仍然只知道 `consultation_session_id`
- `consultation-service` 负责查到 `multimodal_session_id`
- 再代理到 `multimodal-service`

### 方案 B

- 前端直接持有 `multimodal_session_id`
- `gateway-service` 直接代理到 `multimodal-service`

当前已采用方案 A，因为它更符合现有边界，不要求前端额外理解多模态会话路由细节。

---

## 9. 事件产生策略

## 9.1 哪些时机应推送 live 事件

以下时机建议触发 `live_snapshot` 推送：

- 视觉帧处理完成后
- 语音情绪结果完成后
- 文本情绪结果完成后
- turn finalize 后如果 live 有变化

## 9.2 哪些时机不应推送

以下情况不建议推送完整 live：

- 只是收到上传，但还没有新结果
- 状态未发生实际变化

这样可以避免：

- 事件风暴
- 前端无意义重渲染

## 9.3 推送粒度

推荐推送完整 live snapshot，而不是只推差量 patch。

原因：

- 前端实现更简单
- 重连恢复更容易
- 服务端不必维护复杂 patch 协议

在当前 payload 规模下，完整 snapshot 的成本是可接受的。

---

## 10. 分阶段实施结果

## 10.1 Phase 1：去掉 consultation-service 冗余落库

本阶段状态：

- 已完成

完成结果：

1. 从 `consultation-service` 模型中移除：
   - `multimodal_live_payload`
   - `multimodal_live_updated_at`
2. 调整 `get_consultation_multimodal_live()`：
   - 不再写库
   - 不再 `flush()` live 快照
3. 保留 session 兼容键，但不再由数据库字段驱动
4. 已补充迁移脚本删除冗余列

交付结果：

- 立刻减少无意义数据库写入
- 不改变前端 `/multimodal/live` 读取方式

## 10.2 Phase 2：新增 multimodal-service SSE 能力

本阶段状态：

- 已完成

完成结果：

1. 定义 `live/stream` SSE 路由
2. 增加热状态变更后的事件发布机制
3. 在连接建立时先推送一次当前 snapshot
4. 定期发送 heartbeat
5. Redis 不可用时退回服务端 polling 式流

交付结果：

- 服务端具备真正的单向实时推送能力

## 10.3 Phase 3：增加 gateway / consultation 流式代理

本阶段状态：

- 已完成

完成结果：

1. 在 `gateway-service` 增加 SSE 透传
2. 在 `consultation-service` 或 gateway 层完成会话映射
3. 前端统一通过业务域接口订阅

交付结果：

- 前端接入路径与现有 API 风格一致

## 10.4 Phase 4：前端优先使用 SSE，polling 作为降级

本阶段状态：

- 已完成

完成结果：

1. 页面初始化先调用一次 snapshot
2. 建立 `EventSource`
3. 收到 `live_snapshot` 即更新本地状态
4. 流中断时退回 polling
5. 恢复后重新连接 SSE
6. 页面右上角增加 `SSE / HTTP` 传输状态提示

交付结果：

- 正常情况下接近实时
- 异常情况下仍能回退到现有机制

---

## 11. 兼容策略

## 11.1 对前端的兼容

在 SSE 完全稳定前，必须继续保留：

- `/multimodal/live` snapshot 接口

这样即使：

- SSE 代理未部署
- 浏览器流式连接失败
- 某环境不允许长连接

前端仍然可以继续工作。

## 11.2 对 consultation-service 的兼容

第一阶段可以只移除 live 写库副作用，不必一次性重构所有前端状态字段。

也就是说，可以允许前端继续在本地内存里维护：

- `consultation.multimodal_live`
- `consultation.multimodal_live_updated_at`

但这些字段不再作为 `consultation session` 的持久化事实返回。

## 11.3 对下游的兼容

下游正式消费仍然应继续读取：

- turn bundle
- 正式事实表

而不是依赖 live 快照。

---

## 12. 风险与注意事项

## 12.1 不要把 SSE 设计成新的事实源

SSE 只是分发机制，不是数据真源。

真正的真源仍然是：

- 热状态构建逻辑
- 正式事实表

## 12.2 不要把 consultation-service 变成第二个热状态中心

如果 SSE 上线后仍然让 `consultation-service` 同步缓存 live，就会把重复设计继续保留下来。

这应当避免。

## 12.3 要控制事件频率

视觉帧频较高，如果每一帧都无条件广播，可能会造成：

- 连接数压力
- 无意义前端刷新

因此需要有：

- 去重
- 节流
- 仅在状态变化时广播

## 12.4 要保留 snapshot 初始化能力

任何流式方案都不应假设前端从零开始只靠事件就能恢复状态。

必须保留：

- 首次 snapshot
- 断线后 snapshot 补偿

---

## 13. 验收口径

当前实现已经满足以下验收条件：

### Phase 1 验收

- 调用 `/consultations/{id}/multimodal/live` 不再触发 `consultation_sessions` 的 live JSON 更新
- `consultation-service` 不再为 live 读取产生额外数据库写入
- 现有问诊页仍然可以正常显示 live 信息

### Phase 2-4 验收

- 前端可通过 SSE 持续收到 `live_snapshot`
- 新的视觉结果、speech 结果、text 结果能在事件产生后快速反映到看板
- SSE 断开后页面能自动退回 polling
- polling 仍可作为稳定兜底方案

---

## 14. 非目标

本次设计不包含：

- EEG 实时链路设计
- 最终风险结论实时推送
- 用 WebSocket 重写整套前后端通信
- 把所有 live 相关字段一次性从 `multimodal-service` 数据层完全移除

---

## 15. 落地结论

本次按以下顺序落地：

1. 已删除 `consultation-service` 的 `multimodal_live_payload` 冗余落库
2. 已保留 `/live` snapshot 接口作为初始化和降级路径
3. 已在 `multimodal-service` 新增 SSE `live/stream`
4. 已在 `consultation-service` 与 `gateway-service` 增加 SSE 代理
5. 前端已切到“SSE 优先，polling 降级”

当前主链路已完成，可作为后续继续优化 live 热状态与视觉持久化结构的基础版本。
