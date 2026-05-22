# 姿态情绪模态接入系统的代码对齐版实施方案

更新时间：2026-05-22

适用仓库：`depression-system`

---

## 1. 文档目标

本文档只聚焦一个模态：

- `pose`

目标不是重新设计姿态识别算法，而是基于当前仓库代码，整理并推进 `pose` 模态像 `speech / text / face` 一样形成可联调、可回归、可复盘的接入方案。

本文档重点回答四个问题：

1. `pose` 模态接入当前系统是否合理
2. 当前代码已经具备了哪些 pose 接入骨架
3. `pose` 在 `live / bundle / turn / capture` 体系里应处于什么位置
4. 下一步还要补哪些内容，才能把它收成正式走通方案

---

## 2. 先说结论

`pose` 模态接入当前系统是合理的，但它和 `face` 一样，不适合作为问诊主输入，而更适合作为问诊过程中的连续视觉辅助证据。

一句话概括：

**pose 应该是一个“连续采样、短窗口序列推理、turn 级轻状态管理、实时结果进 live、轮次级结果进 bundle”的姿态辅助模态。**

它的单帧价值主要在于：

- 判断是否存在明显姿态倾向
- 看一轮回答里姿态分布是否稳定
- 与 `speech / text / face` 形成辅助互证

因此 pose 的合理接入方式也不是新造一套流程，而是继续挂在统一多模态骨架里：

- `capture`
- `inference result`
- `live`
- `turn bundle`

但这里要特别强调一条当前已经明确的工程结论：

- `pose` 不适合像 `face` 一样被理解成“纯单帧推理模态”
- `pose` 也不适合被实现成“每个 turn 新建一整套 engine”

更合理的目标结构应该是：

- 共享重资源：
  - ONNX `InferenceSession`
  - 必要的 MediaPipe `Pose` 解析资源
- turn 级轻状态：
  - `pose_buffer`
  - `last_used_at`
  - 少量跟踪状态
- turn 结束或超时后清理轻状态

---

## 3. 当前代码里的真实 pose 链路

### 3.1 前端采样

当前问诊页已经在回答窗口内持续截帧，并同时上传 `face` 和 `pose`。

这意味着 pose 当前已经具备真实采样入口，而不是纯规划状态。

### 3.2 consultation-service 的职责

`consultation-service` 当前不做 pose 模型推理，只做：

1. 校验 consultation session 权限
2. 绑定或创建 `multimodal_session_id`
3. 把 pose capture 转发给 `multimodal-service`
4. 如果有 `turn_id`，把上游返回的 `turn_bundle` 缓存到 `consultation_turn.turn_summary_payload`

### 3.3 multimodal-service 的职责

当前 `multimodal-service` 已具备 pose 主链骨架：

1. 记录 `pose` capture
2. 调用 `infer_pose_emotion`
3. 标准化 pose 单帧结果
4. 写入 inference result
5. 刷新 `live.pose`
6. 若有 `turn_id`，更新 `turn_bundle.pose_features`

本轮已继续补齐：

- pose 显式 `failed` 结果
- `sample_count / valid_sample_count` 回灌
- `storage_uri` 回填
- 前端优先消费 `bundle.pose_features`

但按当前代码实现看，仍然有一个很关键的现状问题需要单独指出：

- 当前 `pose` runtime 仍是按 `session_id` 缓存 engine
- engine 内部自带 `pose_buffer`
- 当前没有明确的 turn 切换重置机制

这意味着：

- 当前实现已经支持“短窗口序列推理”
- 但还不能算已经实现了“turn 级轻状态隔离”

所以当前代码状态更准确的描述应是：

**已经具备 session 级序列推理能力，但目标应继续收敛到“共享重资源 + turn 级轻状态”的结构。**

---

## 4. pose 在 live / bundle / turn / capture 中的位置

### 4.1 capture

记录一次姿态帧采样的原始元数据：

- `sample_index`
- `sample_started_at`
- `sample_ended_at`
- `mime_type`
- `storage_uri`

### 4.2 inference result

记录一次单帧 pose 推理的标准结果，核心包括：

- `status`
- `processing_status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `quality_flags`
- `sample_started_at`
- `sample_ended_at`
- `sample_index`
- `error_message`

### 4.3 live.pose

用于前端状态看板实时展示“当前最近的 pose 状态”，当前已承载：

- `status`
- `processing_status`
- `primary_label`
- `primary_score`
- `top_3_labels`
- `quality_flags`
- `latest_capture_at`
- `sample_count`
- `valid_sample_count`
- `error_message`

### 4.4 bundle.pose_features

用于某一轮回答窗口内的姿态聚合结果，是 pose 的正式消费对象。

按当前实现，`pose_features` 已包含：

- `summary_type`
- `primary_label`
- `primary_score`
- `primary_ratio`
- `sample_count`
- `valid_sample_count`
- `label_distribution`
- `quality_distribution`
- `quality_flags`

### 4.5 当前结构与目标结构的差异

当前已经实现的部分：

- `capture -> inference result -> live -> turn bundle`
- pose 短窗口序列模型推理
- 按 `session_id` 复用 pose runtime

当前还没有完全实现的目标部分：

- 按 `turn_id` 管理和隔离 pose 轻状态
- 在 turn 结束时清理 `pose_buffer`
- 在长时间无新帧时超时清理 pose 轻状态

所以从工程角度看，当前 pose 的“主链功能”已经接通，但“运行时状态边界”还没有完全收口。

---

## 5. 当前实施进度（截至 2026-05-22）

当前 pose 已具备的能力包括：

- 前端持续上传 pose 帧
- `multimodal-service` 产出 pose 单帧标准结果
- pose 推理失败时可产出显式 `failed` 结果
- `live.pose` 已带 `processing_status / sample_count / valid_sample_count / error_message`
- `turn_bundle.pose_features` 可稳定生成
- `consultation_turn.turn_summary_payload` 能缓存 pose bundle
- 原始 pose 帧已开始写入对象存储引用 `storage_uri`
- 前端状态面板已优先消费当前轮 `bundle.pose_features`
- 前端 `typecheck` 与生产构建已通过
- `multimodal-service` 的 pose 路由 smoke test 已通过
- `multimodal-service` 的 pose 服务层单元测试已通过
- `consultation-service` 的 pose bundle 缓存单元测试已通过
- 已提供 `scripts/run_pose_modality_checks.ps1` 作为分服务验收脚本

当前仍属于待补齐项的主要是：

- 带真实数据库、对象存储与模型资源的全链路联调
- 更完整的运行期观测与清理策略
- 更真实的 pose 质量规则，例如 `body_cutoff / motion_blur`
- pose runtime 从“session 级缓存带 buffer”收敛到“共享重资源 + turn 级轻状态”

---

## 6. 当前回归与验收方式

如果你本机已有可用的 `Python 3.11+` 环境，可以从仓库根目录执行：

```powershell
.\scripts\run_pose_modality_checks.ps1 -PythonExe "C:\path\to\python.exe"
```

当前脚本会顺序运行：

1. `multimodal-service` 路由 smoke test
2. `multimodal-service` pose 服务层单测
3. `consultation-service` pose bundle 缓存单测

前端侧额外已通过：

- `npm run typecheck`
- `npm run build`

---

## 7. “走通”判定标准

如果项目里要正式宣布“pose 模态接入已经走通”，建议至少同时满足下面 5 条：

1. 采样走通
   - 回答窗口内 pose 帧能持续上传

2. 推理走通
   - `multimodal-service` 能稳定返回 pose 单帧结果或显式失败结果

3. 展示走通
   - `live.pose` 能被前端状态看板稳定消费

4. 归档走通
   - `turn_bundle.pose_features` 能稳定生成并被读取
   - `consultation_turn.turn_summary_payload` 能缓存 pose bundle

5. 复盘与回归走通
   - 页面刷新后当前轮 pose 结果不丢
   - pose 最小回归脚本可重复执行

---

## 8. 下一步建议

当前 pose 的下一步不应该直接进入真实测试，而应该先按阶段把运行时结构收紧，再进入联调。

### Phase A：方案冻结

当前状态：

- 已完成（2026-05-22）

先冻结一个明确目标：

- 不走“每 turn 新建 engine”
- 改走“共享重资源 + turn 级轻状态”

这一阶段的目标是统一口径，不做代码实现。

#### Phase A 冻结结论

本阶段已经确认以下 4 条结论，后续实现不再反复摇摆：

1. `pose` 不改造成纯单帧推理模态
2. `pose` 不按 `turn` 新建完整 runtime engine
3. `pose` 保留短窗口序列推理能力
4. `pose` 的运行时结构改造目标是：
   - 共享重资源
   - turn 级轻状态
   - turn 结束或超时后清理轻状态

#### 当前结构 vs 目标结构

| 维度 | 当前结构 | 目标结构 |
| --- | --- | --- |
| 重资源持有方式 | `session_id` 级 pose engine 常驻 | 全局/进程级共享重资源 |
| 轻状态位置 | 混在 engine 内部 `pose_buffer` | 独立的 turn 级轻状态 |
| 状态隔离边界 | 主要是 `session_id` | `session_id + turn_id` |
| turn 切换行为 | 当前无明确 reset 机制 | turn 切换时重置/替换轻状态 |
| 资源风险 | 容易从业务状态演变成 session 常驻积累 | 重资源稳定复用，轻状态可清理 |
| 与模型特性匹配度 | 已保留序列模型，但状态边界过粗 | 保留序列模型，状态边界与业务一致 |

#### Phase A 输出物

本阶段的输出不是代码，而是冻结后的实施口径：

- 运行时改造目标已明确
- 不推荐方案已明确排除
- 后续 `Phase B / C / D` 的顺序已固定

### Phase B：运行时结构改造

当前状态：

- 已完成核心结构改造（2026-05-22）

这一阶段的目标是把 pose runtime 从当前的 session 级 buffer 缓存，改成更合理的结构：

- 共享重资源：
  - ONNX `InferenceSession`
  - MediaPipe `Pose`
- 独立轻状态：
  - `pose_buffer`
  - `last_used_at`
  - 少量跟踪状态
- 状态 key：
  - `session_id + turn_id`

这一阶段的关键原则是：

- turn 级隔离轻状态
- 不按 turn 重建重资源

#### Phase B 已完成内容

本阶段已完成的核心改造包括：

1. pose 重资源与轻状态已经开始拆分：
   - 共享 `pose` runtime engine
   - turn 级 pose state

2. `pose_buffer` 已从 engine 内常驻状态改为 turn 级状态承载

3. pose 推理请求已开始透传 `turn_id`

4. runtime store 已具备：
   - 共享 pose engine 获取
   - `session_id + turn_id` 维度的 pose 轻状态获取

5. Phase B 相关最小回归已通过：
   - `test_multimodal_pose_service.py`
   - `test_multimodal_routes.py`
   - `test_non_eeg_routes.py`

#### Phase B 尚未处理的内容

本阶段没有继续处理以下内容，这些应留到 `Phase C`：

- turn 完成后的状态清理
- 无新帧超时清理
- 异常路径兜底清理
- 更细粒度的运行期观测字段

### Phase C：生命周期治理

当前状态：

- 已完成核心生命周期治理（2026-05-22）

这一阶段需要补齐：

1. turn 完成后清理对应 pose 轻状态
2. 长时间无新帧时超时清理 pose 轻状态
3. 异常路径下的兜底清理

#### Phase C 已完成内容

本阶段已完成的治理包括：

1. runtime store 已支持：
   - `clear_pose_turn_state(...)`
   - `prune_pose_turn_states(...)`

2. pose turn state 已支持惰性超时清理：
   - 在获取 turn state 时自动执行 idle prune

3. `multimodal-service` 已提供 pose turn runtime 清理接口

4. `consultation-service` 已在 turn 提交完成后触发 pose turn runtime 的 best-effort 清理

5. 清理失败不会反向阻塞 consultation turn 主链提交

6. Phase C 相关最小回归已通过：
   - `test_multimodal_pose_service.py`
   - `test_multimodal_routes.py`
   - `test_non_eeg_routes.py`
   - `test_consultation_pose_capture_service.py`
   - `test_consultation_pose_runtime_cleanup.py`

#### Phase C 后的状态

到这一阶段为止，pose 已经具备：

- 共享重资源
- turn 级轻状态
- turn 完成清理
- idle 超时清理

后续如果还要继续增强，重点就不再是主生命周期缺口，而是：

- 更细的运行期观测
- 更完整的清理指标暴露
- 真实环境联调下的行为验证

### Phase D：真实环境联调

只有在前面三步完成后，才建议进入真实 DB / MinIO / 模型资源联调。

当前状态：

- 已完成核心真实环境联调（2026-05-22）

本阶段已完成的验证包括：

1. 真实容器重建与健康检查
   - `consultation-service`、`multimodal-service` 在 Docker 开发环境下重新构建并通过 `/health/ready`
   - 先暴露出一次真实环境漂移问题：运行中的 `consultation-service` 容器仍在使用旧版 `create_multimodal_session(owner_session_id, user_id)` 签名
   - 重建后确认容器内代码已切换到当前实现：`create_multimodal_session(user_id, encounter_session_id, flow_type, flow_run_id)`

2. 真实问诊主链联调
   - 已成功创建 consultation session，并同步创建 multimodal session
   - 已成功启动问诊、完成系统欢迎项，并进入 `waiting_user_input`
   - 已成功拿到真实 `current_turn_id`

3. 真实 pose 采样与聚合验证
   - 在真实 `waiting_user_input` turn 下连续提交 8 个 pose capture
   - `live.pose` 已在真实环境下更新为 `ready/completed`
   - 已验证 `sample_count=8`、`valid_sample_count=1`
   - 已验证 `turn_bundle.pose_features` 正常生成并可经 consultation-service 查询

4. 真实 turn 提交与清理链验证
   - 已成功提交至少 2 个真实问诊 turn
   - 已验证 `pose capture -> live -> bundle -> submit turn` 主链成立
   - 联调过程中暴露出一个真实 bug：`multimodal-service` 的 `clear_pose_turn_runtime_state(...)` 缺少模块级 `runtime_store` 导入，导致 `pose-runtime/clear` 路由 500
   - 该问题已在真实环境中修复并重建容器验证
   - 修复后再次验证：提交新 turn 后，继续直连 `pose-runtime/clear` 返回 `cleared=false`，说明 consultation-service 的 best-effort 清理已先一步完成

本阶段结论：

- `pose` 在真实 Docker 开发环境下已经跑通：
  - `consultation -> multimodal session`
  - `pose capture -> live.pose`
  - `pose capture -> turn_bundle.pose_features`
  - `submit turn -> best-effort runtime clear`
- `Phase D` 已不再停留在“建议联调”，而是已经完成最关键的真实环境闭环验证
- 后续如果继续扩大测试范围，重点应转向：
  - 更多真实图像/摄像头输入样本
  - face + pose 并发联调
  - 运行期指标和清理观察
  - 端到端前端页面实机操作复验

建议顺序：

1. 先完成 pose runtime 结构改造
2. 再补运行期观测与清理策略
3. 最后跑真实环境联调
4. pose 收稳后，再和 `face` 一起做视觉模态公共层收敛

---

## 9. 最终结论

当前仓库里的 pose 模态接入方向总体是合理的，而且已经不只是“有接口”，而是具备了：

- 前端持续采样
- consultation-service 转发
- multimodal-service 推理
- `live.pose` 实时更新
- `turn_bundle.pose_features` 聚合归档
- 前端正式消费 bundle
- 跨服务最小回归脚本

如果一句话总结这份方案，就是：

**pose 应作为问诊过程中的连续姿态辅助模态，保留短窗口序列推理特性，但把运行时结构收敛为“共享重资源 + turn 级轻状态”；实时结果进 live，正式结果进 bundle，不阻塞 turn 主流程。**
