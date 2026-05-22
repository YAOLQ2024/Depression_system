# face / pose 重复代码收敛与冗余清理计划

更新时间：2026-05-22

适用仓库：`depression-system`

---

## 1. 文档目标

本文档只解决一个问题：

**在 `face` 和 `pose` 两个视觉模态都已经基本走通后，如何针对当前仓库的真实代码结构，做一轮简单、低风险、可落地的重复代码收敛与冗余清理。**

本文档不做两件事：

- 不重新设计视觉模态架构
- 不在本阶段引入“大而全”的抽象层

原则很明确：

- 只收敛已经被 `face + pose` 共同验证过的重复逻辑
- 只清理已经确认没有继续保留价值的冗余
- 以“小步整理、保持现有链路稳定”为优先

---

## 2. 当前为什么适合开始收敛

当前 `face` 和 `pose` 都已经具备：

- 前端持续采样入口
- `consultation-service` capture 转发
- `multimodal-service` 单帧推理
- `live` 更新
- `turn_bundle` 聚合
- `consultation_turn.turn_summary_payload` 缓存
- 最小回归脚本

这意味着：

- 视觉模态主链已经不是“只落了一个 face”，而是两个模态都跑通了
- 重复逻辑已经显现出来
- 现在收敛比更早抽象更稳，因为共性已经经过两条链路验证

---

## 3. 当前已确认的重复点和冗余点

### 3.1 consultation-service：face / pose capture 提交逻辑重复

位置：

- [consultation_engine.py](/D:/LQ/pythonProject/depression-system/services/consultation-service/app/services/consultation_engine.py:1532)
- [consultation_engine.py](/D:/LQ/pythonProject/depression-system/services/consultation-service/app/services/consultation_engine.py:1582)

当前问题：

- `submit_consultation_face_capture`
- `submit_consultation_pose_capture`

两段逻辑几乎完全一致，差异主要只有：

- 上游调用函数不同
- 错误码不同
- 模态名不同

风险：

- 后面修一边容易漏另一边
- 视觉模态字段再扩时会重复改两遍

### 3.2 前端 API：face / pose capture 请求函数重复

位置：

- [consultation.api.ts](/D:/LQ/pythonProject/depression-system/apps/consultation/client/src/services/api/consultation.api.ts:82)

当前问题：

- `submitConsultationFaceCapture`
- `submitConsultationPoseCapture`

除了 URL 不同，本质一致。

### 3.3 前端状态层：face / pose capture action 重复

位置：

- [useConsultationApp.ts](/D:/LQ/pythonProject/depression-system/apps/consultation/client/src/app/useConsultationApp.ts:542)

当前问题：

- `submitConsultationFaceCapture`
- `submitConsultationPoseCapture`

两段逻辑只是：

- 调不同 request
- 调同一个 merge
- 报错文案不同

### 3.4 文档与脚本：face / pose 回归入口已对称，后续有继续复制的风险

位置：

- `scripts/run_face_modality_checks.ps1`
- `scripts/run_pose_modality_checks.ps1`
- 多处 README

当前判断：

- 这两份脚本当前不是“该删的冗余”
- 它们解决了两个服务都叫 `app` 包、不能共用一个 `PYTHONPATH` 的实际问题

但需要注意：

- 后续如果再做 EEG 或别的模态，不建议继续一模态一脚本地复制

### 3.5 legacy 路由兼容层仍在

位置：

- [non_eeg_inference.py](/D:/LQ/pythonProject/depression-system/services/multimodal-service/app/api/non_eeg_inference.py:13)

当前问题：

- 仍同时保留：
  - 新路径 `/api/v1/non-eeg/...`
  - 旧兼容路径 `/api/v1/text/infer`、`/api/v1/audio/infer`、`/api/v1/emotion-recognition/frame-infer`、`/api/v1/pose/frame-infer`

当前判断：

- 这是明确的维护成本
- 但在没有确认外部调用方全部迁走之前，不建议当前阶段直接删除

### 3.6 小型噪音

示例：

- 局部未使用变量
- 文档说明在多个文件里重复描述同一命令

这类问题可以顺手清，但不应抢在主重复逻辑之前做。

---

## 4. 本轮改造目标

本轮只做 3 件事：

1. 抽公共函数，合并 `consultation-service` 的 `face / pose` capture 提交流程
2. 抽公共函数，合并前端 `face / pose` capture API 和 action
3. 顺手清掉少量已经确认的低风险噪音

本轮不做：

1. 不删除 legacy 路由
2. 不重构 `multimodal-service` 的 `face / pose` 推理主链
3. 不重写现有回归脚本体系
4. 不做大规模文档合并

---

## 5. 详细实施方案

### Step 1：收敛 consultation-service 的重复 capture 逻辑

当前状态：

- 已完成（2026-05-22）

目标：

- 把 `submit_consultation_face_capture`
- `submit_consultation_pose_capture`

收成一个内部公共 helper，再由两个公开函数薄封装。

建议做法：

新增一个内部函数，例如：

- `_submit_consultation_frame_capture(...)`

它统一处理：

- `acting_user_id` 校验
- `session_record` 获取
- `multimodal_session_id` 绑定
- 上游 capture 请求
- `turn_summary_payload` 缓存
- `db_session.flush()`

保留外层公开函数：

- `submit_consultation_face_capture`
- `submit_consultation_pose_capture`

原因：

- 对外接口名不变
- 风险小
- 回归范围可控

已完成情况：

- 已新增内部 helper：`_submit_consultation_frame_capture(...)`
- `submit_consultation_face_capture(...)` 与 `submit_consultation_pose_capture(...)` 已改为薄封装
- `consultation-service` 相关回归已通过：
  - `test_consultation_face_capture_service.py`
  - `test_consultation_pose_capture_service.py`

### Step 2：收敛前端 API 请求函数

当前状态：

- 已完成（2026-05-22）

目标：

- 合并 `submitConsultationFaceCapture`
- 合并 `submitConsultationPoseCapture`

建议做法：

新增一个内部 API helper，例如：

- `submitConsultationFrameCapture(sessionId, modality, payload)`

外层保留薄封装：

- `submitConsultationFaceCapture(...)`
- `submitConsultationPoseCapture(...)`

原因：

- 保持调用层语义清晰
- 避免让页面层直接传字符串 URL

已完成情况：

- 已新增内部 helper：`submitConsultationFrameCapture(sessionId, modality, payload)`
- `submitConsultationFaceCapture(...)` 与 `submitConsultationPoseCapture(...)` 已改为薄封装
- 前端静态验证已通过：
  - `npm run typecheck`
  - `npm run build`

### Step 3：收敛前端 action 层重复逻辑

当前状态：

- 已完成（2026-05-22）

目标：

- 合并 `useConsultationApp.ts` 中 face / pose 两段 submit action

建议做法：

新增一个内部 action helper，例如：

- `submitConsultationFrameCapture(modality, payload)`

统一处理：

- consultation 空值判断
- request 调用
- `mergeFrameCaptureResponseIntoConsultation(...)`
- 错误处理

外层仍暴露：

- `submitConsultationFaceCapture`
- `submitConsultationPoseCapture`

这样可以保持组件侧 API 不变。

已完成情况：

- 已新增内部 helper：`submitConsultationFrameCapture(modality, payload, request, fallbackErrorMessage)`
- `submitConsultationFaceCapture(...)` 与 `submitConsultationPoseCapture(...)` 已改为薄封装
- 前端静态验证已通过：
  - `npm run typecheck`
  - `npm run build`

### Step 4：顺手清理小型噪音

当前状态：

- 已完成（2026-05-22）

目标：

- 删掉已确认无意义的局部噪音

优先级低，只建议顺手做：

- 未使用变量
- 明显重复但没有必要继续存在的内部小片段

不建议本阶段花太多时间在：

- 大规模改文档结构
- 把多个 README 强行合并

已完成情况：

- 已清理已确认的局部噪音：
  - 删除 `multimodal_session_service.py` 中无意义的 `gray = None`
- 已重新跑通视觉模态最小回归：
  - `run_face_modality_checks.ps1`
  - `run_pose_modality_checks.ps1`
- 后端语法检查已通过：
  - `py_compile services/multimodal-service/app/services/multimodal_session_service.py`

---

## 6. 本轮不建议处理的内容

### 6.1 legacy 路由删除

虽然它是冗余来源之一，但当前还不建议现在删除。

原因：

- 还没有做全仓库和外部调用确认
- 删除成本比当前收益大

更合适的做法是：

- 先做调用方盘点
- 再单独出一份 legacy API 退役计划

### 6.2 face / pose 推理主链深度抽象

当前 `face` 和 `pose` 在 `multimodal-service` 里虽然相似，但还存在真实差异：

- `quality_flags` 不同
- `processing_status` 语义不完全一致
- 失败态、采样有效性、聚合口径也不同

所以本轮不建议把它们强行抽成一个统一的“视觉推理模板函数”。

### 6.3 回归脚本统一成一个“万能模态脚本”

当前 `run_face_modality_checks.ps1` 和 `run_pose_modality_checks.ps1` 已经可用。

如果现在硬合成一个超通用脚本，收益不大，反而容易把简单脚本搞复杂。

---

## 7. 推荐实施顺序

建议严格按下面顺序推进：

1. `consultation-service` capture 公共 helper
2. 前端 API capture 公共 helper
3. 前端 action capture 公共 helper
4. 顺手清理局部噪音
5. 最后重新跑 `face` 和 `pose` 回归

原因：

- 后端业务编排层重复最明显，收益最高
- 前端 API 和 action 重复次之
- 小噪音最后顺手做最稳

---

## 8. 验收标准

本轮改造完成后，至少要满足下面 6 条：

1. `face` 现有能力不回退
2. `pose` 现有能力不回退
3. 前端 `typecheck` 通过
4. 前端 `build` 通过
5. `run_face_modality_checks.ps1` 通过
6. `run_pose_modality_checks.ps1` 通过

额外要求：

- 外层公开函数名尽量不变
- 当前页面调用方式尽量不变
- 当前方案文档口径不需要重写

---

## 9. 最终结论

当前最适合这套项目的做法不是“大重构”，而是：

**在保持 `face / pose` 已有链路稳定的前提下，先收敛 consultation-service 和前端里最明显的重复 capture 逻辑，再顺手清理小型冗余。**

这轮改造的目标不是“把视觉模态抽象得多漂亮”，而是：

- 让后续维护不需要改两遍
- 让 `face / pose` 继续并行演进时更稳
- 给下一步更大范围的视觉模态收敛留出干净基础
