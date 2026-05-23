# 视觉模态共享输入重构实施方案

更新时间：2026-05-23

适用仓库：`depression-system`

---

## 1. 文档目标

本文档用于指导 `face` 和 `pose` 两个视觉模态，从当前的：

- 前端一次截图
- 分别发起两次请求
- 后端分别按两条 capture 链路处理

演进到推荐目标态：

- **共享输入**
- **分离模态处理**

也就是：

- 前端一次上传 `visual frame`
- 后端只保存一次共享输入
- 后端内部再分发到：
  - `face inference`
  - `pose inference`

本文档是正式实施方案，不是讨论稿。

---

## 2. 当前现状

当前系统已经具备以下条件：

1. 前端采样层已经是“一次截图”
2. `face` 和 `pose` 已经都能走到：
   - `capture`
   - `inference`
   - `live`
   - `turn_bundle`
3. `pose` 已经完成：
   - 共享重资源
   - turn 级轻状态
   - 生命周期治理

但当前仍处于中间态：

- 前端共享截图
- 后端仍按 `face` / `pose` 两次独立 capture 请求分别处理

所以当前系统还不是完整的：

- **共享输入、分离模态处理**

---

## 3. 为什么现在值得做这次重构

### 3.1 当前结构已经暴露出重复

现在每次视觉采样都会：

- 发一次 `face capture`
- 发一次 `pose capture`

这意味着：

- 两次 HTTP 请求
- 两次 consultation-service 转发
- 两次 multimodal-service capture 入口
- 两份近似的输入上下文

### 3.2 当前结构不利于后续继续扩展

如果后面再加新的视觉子模态，例如：

- eye gaze
- head pose
- micro-expression

继续沿用“前端同一张图发 N 次请求”，扩展成本会越来越高。

### 3.3 当前结构不利于统一视觉时刻对齐

虽然现在 `face` 和 `pose` 来自同一张截图，但在后端并没有一个明确的“共享视觉帧实体”。

这会导致：

- 原始帧留档分散
- 后续做同一时刻对齐分析不够自然
- 更难支撑统一视觉调度

---

## 4. 重构目标

本次重构的目标不是重写整套多模态系统，而是只收敛视觉链路。

### 4.1 最终目标结构

推荐结构如下：

1. 前端只上传一次 `visual frame`
2. 后端只保存一次共享视觉输入
3. 后端内部派生两条模态处理：
   - `face`
   - `pose`
4. 结果仍然分别进入：
   - `live.face`
   - `live.pose`
   - `turn_bundle.face_features`
   - `turn_bundle.pose_features`

### 4.2 本次不变的部分

以下部分本次不推翻：

- `speech` / `text` 链路
- `multimodal_inference_results` 作为推理结果表
- `multimodal_turn_bundles` 作为正式聚合层
- `consultation_sessions.multimodal_live_payload`
- `consultation_turns.turn_summary_payload`

---

## 5. 设计原则

### 5.1 共享输入，不共享结果状态

这次要共享的是：

- 原始截图
- 时间戳
- 上下文元数据

但不应该强行共享：

- `face` 状态
- `pose` 状态
- `face` 聚合口径
- `pose` 聚合口径

### 5.2 保留模态特性差异

- `face` 仍然可以更偏单帧
- `pose` 仍然保留短时窗口序列推理

重构目标是统一输入层，不是抹平模型差异。

### 5.3 先新增新链路，再退役旧链路

本次不建议直接删旧的：

- `/captures/face`
- `/captures/pose`

应该先新增：

- `/captures/visual`

等新链路稳定后，再考虑旧接口降级或退役。

### 5.4 优先复用现有落表与聚合能力

本次重构优先收敛：

- capture 入口
- 原始帧留档
- fan-out 调度

尽量不推翻现有：

- inference result 记录
- live 更新
- bundle 聚合

---

## 6. 目标结构

### 6.1 当前结构

当前结构可描述为：

1. 前端截图一次
2. 同时发起：
   - `POST /captures/face`
   - `POST /captures/pose`
3. 后端各自保存 capture
4. 各自执行推理
5. 各自更新 `live/bundle`

### 6.2 目标结构

目标结构应改成：

1. 前端截图一次
2. 发起：
   - `POST /captures/visual`
3. 后端保存一条共享视觉帧记录
4. 后端内部派生：
   - `face inference`
   - `pose inference`
5. 各自更新 `live/bundle`

---

## 7. 数据设计建议

### 7.1 推荐新增共享视觉帧表

建议新增：

- `multimodal_visual_frames`

建议字段：

- `id`
- `session_id`
- `turn_id`
- `flow_run_id`
- `stage_id`
- `question_key`
- `sample_index`
- `sample_started_at`
- `sample_ended_at`
- `mime_type`
- `storage_uri`
- `capture_payload`
- `captured_at`
- `created_at`

作用：

- 作为共享输入层的正式实体
- 只保存一次原始视觉帧元数据

### 7.2 现有推理结果表继续使用

继续保留：

- `multimodal_inference_results`

区别是：

- `face` 和 `pose` 的 `source_ref_id` 或 `sample_id` 应关联到共享视觉帧

### 7.3 现有 bundle 表继续使用

继续保留：

- `multimodal_turn_bundles`

不重新设计聚合层。

---

## 8. 接口设计建议

### 8.1 新增 consultation-service 入口

建议新增：

- `POST /consultations/{session_id}/multimodal/captures/visual`

请求包含：

- `question_key`
- `turn_id`
- `sample_started_at`
- `sample_ended_at`
- `sample_index`
- `mime_type`
- `image_file`

### 8.2 新增 multimodal-service 入口

建议新增：

- `POST /api/v1/multimodal/sessions/{session_id}/captures/visual`

作用：

- 接收共享视觉帧
- 保存共享输入记录
- 内部分发 `face` 与 `pose`
- 返回组合响应

### 8.3 响应结构建议

建议返回：

- `visual_frame`
- `face_result`
- `pose_result`
- `turn_bundle`
- `multimodal_session`

注意：

- 返回是组合响应
- 但内部结果仍保持按模态分开

---

## 9. 运行时设计建议

### 9.1 共享输入层

在 `multimodal-service` 中增加一个共享视觉输入处理层，负责：

- 原始图片落存储
- 共享视觉帧记录落库
- 统一生成 `visual_frame_id`

### 9.2 模态分发层

共享输入处理完成后，内部调用：

- `face` 推理逻辑
- `pose` 推理逻辑

要求：

- 两者可以共享图像输入
- 但不要共享状态机

### 9.3 pose 保留现有 turn 级轻状态

`pose` 继续保持：

- 共享重资源
- turn 级轻状态
- turn 完成与超时清理

本次重构不要回退到 session 常驻 buffer。

---

## 10. 分阶段实施方案

### Phase A：方案冻结

当前状态：**已完成（2026-05-23）**

目标：

- 冻结共享输入设计
- 冻结“新增不替换”的实施边界

产出：

- 本文档评审通过
- 确认是否新增 `multimodal_visual_frames`
- 确认 consultation-service 与 multimodal-service 的新接口契约

#### Phase A 冻结结论

本阶段已经冻结以下结论，后续 Phase B 及以后默认按此执行：

1. 本次重构只收敛视觉链路，不重做整套多模态架构。
2. 本次重构目标是：
   - 共享视觉输入
   - 分离 `face / pose` 处理
3. 本次不改变：
   - `speech` / `text` 主链
   - `live` / `bundle` 的总体分层
   - `pose` 的 turn 级轻状态设计
4. 本次不允许把 `pose` 降级为纯单帧情绪识别。
5. 本次不允许把 `face` 和 `pose` 强行合并成一个统一视觉结果状态。
6. 本次实施顺序固定为：
   - 先新增共享视觉帧入口
   - 再让前端切换到单次 visual capture
   - 最后再考虑旧 `face/pose` capture 接口退役

#### Phase A 边界确认

当前明确纳入本轮实施范围的内容：

- 新增共享视觉输入实体
- 新增 `/captures/visual` 前后端接口
- 后端内部 `face + pose` fan-out
- 前端由双请求切到单请求
- 旧接口过渡期兼容

当前明确不纳入本轮实施范围的内容：

- 语音 / 文本链路重构
- 多模态数据库整体改版
- WebSocket / SSE 实时推送替代 live 轮询
- 把所有 multimodal 文档目录与文件名一起重命名
- 把 `non_eeg_*` 相关命名在本阶段全部替换完

#### Phase A 当前结构 vs 目标结构

当前结构：

- 前端一次截图
- 前端发两条请求：
  - `face capture`
  - `pose capture`
- 后端分两条 capture 链路处理
- `live / bundle` 分别按模态更新

目标结构：

- 前端一次截图
- 前端发一条 `visual capture`
- 后端保存一次共享视觉帧
- 后端内部派生：
  - `face inference`
  - `pose inference`
- `live / bundle` 仍分别按模态更新

#### Phase A 进入下一阶段的条件

进入 Phase B 前，默认认为以下事项已确定：

- 共享输入是目标态
- 分离模态处理是硬约束
- 旧双接口不能立即删除
- 结果层继续沿用现有 `inference_result + turn_bundle + live` 结构
- `pose` 继续保留 turn 级轻状态与生命周期治理

### Phase B：新增共享视觉帧数据层

当前状态：**已完成（2026-05-23）**

目标：

- 新增视觉共享输入实体
- 不改旧 `face/pose` 接口行为

实施内容：

1. 新增视觉帧模型与 migration
2. 新增对象存储路径约定
3. 新增视觉帧写入 helper

验收：

- 可写入共享视觉帧记录
- 不影响现有 `face/pose` 链路

#### Phase B 已完成内容

本阶段已完成以下数据层改造：

1. 新增 `MultimodalVisualFrame` model
2. 新增 Alembic migration：
   - `20260523_0010_create_multimodal_visual_frames.py`
3. 新增共享视觉帧数据层 helper：
   - `_build_visual_frame_storage_uri(...)`
   - `_record_visual_frame(...)`
4. 已将新 model 注册进 `app.models.__init__`

#### Phase B 当前结论

到本阶段结束时，系统已经具备：

- 共享视觉输入实体定义
- 对应数据库迁移脚本
- 服务层最小写入落点

但仍然**没有**改变以下行为：

- 前端仍然是 `face + pose` 双请求
- consultation-service 仍然没有 `/captures/visual`
- multimodal-service 仍然没有 `/captures/visual`
- 现有 `face/pose` capture 链路保持不变

这符合 Phase B 的边界：先把共享输入数据层打底，不提前改接口行为。

### Phase C：新增 visual capture 接口

当前状态：**已完成（2026-05-23）**

目标：

- 打通前后端单次视觉上传链路

实施内容：

1. `consultation-service` 新增 `/captures/visual`
2. `multimodal-service` 新增 `/captures/visual`
3. `gateway-service` 新增 `/captures/visual` 转发入口
4. 内部 fan-out 到 `face + pose`

验收：

- 一次请求可产出 `face_result + pose_result`
- 共享输入只落一次

#### Phase C 已完成内容

本阶段已完成以下接口层改造：

1. `multimodal-service` 新增：
   - `POST /api/v1/multimodal/sessions/{session_id}/captures/visual`
2. `consultation-service` 新增：
   - `POST /api/v1/consultations/{session_id}/multimodal/captures/visual`
3. `gateway-service` 新增：
   - `POST /api/v1/consultations/{session_id}/multimodal/captures/visual`
   - 用于把浏览器请求继续转发到 `consultation-service`
4. `consultation-service` 上游 client 新增 `submit_visual_capture(...)`
5. `multimodal-service` 内部新增 `submit_visual_capture(...)`
6. 单次 visual capture 已可返回：
   - `visual_frame`
   - `face_result`
   - `pose_result`
   - `turn_bundle`
   - `multimodal_session`

#### Phase C 当前结论

到本阶段结束时，系统已经具备：

- 后端单次视觉上传入口
- `gateway-service -> consultation-service -> multimodal-service` 的完整转发链路
- 后端内部 `face + pose` fan-out 处理能力
- consultation-service 到 multimodal-service 的转发链路

但仍然**没有**改变以下行为：

- 前端页面仍在调用旧的 `face + pose` 双请求
- 旧双接口仍然保留并可继续使用

这符合 Phase C 的边界：先把新接口打通，再在 Phase D 切前端。

#### Phase C 已完成验证

本阶段已完成的最小验证包括：

- `py_compile` 通过
- `multimodal-service` 路由测试通过：
  - `test_multimodal_routes.py`
  - 结果：`6 passed`
- `consultation-service` visual capture 服务测试通过：
  - `test_consultation_visual_capture_service.py`
  - 结果：`1 passed`

说明：

- 默认系统 Python 环境缺少部分依赖，无法直接跑完整测试
- 本次路由与服务层测试使用项目现有临时测试环境完成

#### Phase C 真实联调补充

在 HTTPS 浏览器联调阶段，曾实际暴露出一处容易忽略的问题：

- 前端与 `consultation-service`、`multimodal-service` 的 `/captures/visual` 已经加好
- 但 `gateway-service` 最初没有同步新增：
  - `POST /api/v1/consultations/{session_id}/multimodal/captures/visual`
- 结果表现为浏览器请求：
  - `/api/v1/consultations/{session_id}/multimodal/captures/visual`
  - 返回 `404 Not Found`

已修正结论：

- 新增视觉主链时，不能只改 consultation 与 multimodal 两层
- 网关层必须同步补齐同名转发路由

部署提醒：

- 如果后续再次新增类似的 consultation 路由，至少要同步重建：
  - `gateway-service`
- 若前端也刚切换到新接口，建议一起重建：
  - `consultation`
  - `consultation-service`
  - `gateway-service`

### Phase D：前端切换到单次 visual capture

当前状态：**已完成（2026-05-23）**

目标：

- 前端不再双请求上传同一张图

实施内容：

1. 新增 `submitConsultationVisualCapture`
2. 页面改成一次截图、一条请求
3. 保持 `live/bundle` 页面消费不回归

验收：

- 浏览器 Network 中每轮视觉采样只剩 1 条视觉上传请求
- `face/pose` 状态仍正常更新

#### Phase D 已完成内容

本阶段已完成以下前端改造：

1. 前端新增 `submitConsultationVisualCapture(...)`
2. `consultation.api.ts` 已新增 `/multimodal/captures/visual` 请求封装
3. `useConsultationApp.ts` 已新增 visual capture 状态合并逻辑
4. `ConsultationPage.tsx` 已从：
   - `submitConsultationFaceCapture(payload)`
   - `submitConsultationPoseCapture(payload)`
   切换为：
   - `submitConsultationVisualCapture(payload)`

#### Phase D 当前结论

到本阶段结束时，前端已完成：

- 单次截图
- 单次视觉上传请求
- 由后端内部 fan-out 到 `face + pose`

这意味着当前页面在视觉采样这一层，已经正式从：

- 前端共享截图 + 前端双请求

演进到：

- 前端共享截图 + 前端单请求 + 后端内部双模态处理

#### Phase D 已完成验证

本阶段已完成的前端验证包括：

- `npm run typecheck` 通过
- `npm run build` 通过

补充说明：

- 当前仍有 Vite chunk size warning
- 该 warning 为既有现象，不是本次 visual capture 切换引入的问题

### Phase E：旧接口降级与清理

当前状态：**已完成第一阶段清理（2026-05-23）**

目标：

- 收敛技术债

实施内容：

1. 保留旧接口一段观察期
2. 确认无调用方后再退役
3. 清理相关重复逻辑

验收：

- 前端已完全不依赖旧双接口
- 旧接口可以降为兼容层或删除

#### Phase E 已完成内容

本阶段当前已完成的第一阶段清理包括：

1. 前端主链已不再依赖旧的：
   - `submitConsultationFaceCapture(...)`
   - `submitConsultationPoseCapture(...)`
2. 前端 API 层已移除旧双上传封装
3. 前端状态管理层已移除旧双上传 action
4. 当前视觉主链只保留：
   - `submitConsultationVisualCapture(...)`

#### Phase E 当前结论

到当前阶段结束时：

- 前端已经完全切到新 visual capture 主链
- 旧 `face/pose` 上传接口仍保留在后端，作为兼容层存在
- 这意味着系统已经进入“前端完成切换、后端保留观察期兼容”的状态

#### Phase E 下一步建议

后续如果继续做第二阶段清理，可按下面顺序推进：

1. 在 README / 服务文档中明确标记旧 `face/pose` capture 为兼容入口
2. 观察一段时间确认无调用方
3. 再删除 consultation-service 与 multimodal-service 的旧双接口及对应测试

---

## 11. 风险与注意事项

### 11.1 不要把视觉结果强行合并成一个状态

风险：

- `face` 和 `pose` 的状态语义不同
- `pose` 可能仍处于 `collecting`
- `face` 可能已经 `ready`

因此只能共享输入，不能强行共享结果状态。

### 11.2 不要让 pose 退回到纯单帧逻辑

本次收敛的是输入层，不是降低模型要求。

`pose` 仍应保留：

- landmarks 提取
- turn 级 buffer
- 序列推理

### 11.3 不要一次性删掉旧接口

如果直接删旧接口，联调风险太高。

更稳的方式是：

- 新链路上线
- 前端切换
- 观察稳定
- 再退役旧链路

---

## 12. 当前建议结论

如果你决定现在开始做这次重构，我的建议是：

- **值得做**
- **但只做视觉链路收敛**
- **不做整套多模态系统推倒重写**

一句话总结：

**本次应实施“共享视觉输入 + 分离 face/pose 处理”的收敛式重构，而不是重写整套多模态架构。**
