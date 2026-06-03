# Preview Complete Step 4 实施说明

更新时间：2026-06-03

对应设计文档：

- `docs/apps/consultation/greeting-auto-advance-and-seamless-video-switch-design_20260602.md`

## 1. 本步产物

本步在 `consultation-service` 中正式落下咨询会话 `preview-complete` 接口，并把前端底层预取调用切到新接口。

后端代码入口：

- API 路由：`services/consultation-service/app/api/consultations.py`
- 服务实现：`services/consultation-service/app/services/consultation_engine.py`

前端低层接线：

- API client：`apps/consultation/client/src/services/api/consultation.api.ts`
- app store action：`apps/consultation/client/src/app/useConsultationApp.ts`

## 2. 新增接口

新增接口：

- `POST /api/v1/consultations/{session_id}/question-items/{question_key}/preview-complete`

返回格式沿用现有成功响应包装，`data.consultation` 中返回的是“推演后的下一节点会话快照”，而不是已经正式提交的数据库状态。

## 3. 实现策略

`preview_system_question_item_completion(...)` 与正式 `complete_system_question_item(...)` 共享同一套：

- 系统题完成前置校验
- 当前节点合法性校验
- `speak_then_complete` 节点推进逻辑
- `_move_to_target(...)`
- `_auto_advance(...)`
- `_sync_playlist_state(...)`

实现上先在 SQLAlchemy session 内复用正式推进逻辑生成预览态，再：

1. 调用 `_serialize_session(...)` 生成预览返回值
2. 立即执行 `db_session.rollback()`
3. 返回预览 payload

这样可以保证：

- preview 与正式 complete 走同一套状态推进规则
- preview 不持久化 `session_record.status`
- preview 不持久化 `current_question_key/current_node_id`
- preview 不提前创建正式下一轮会话状态

## 4. 前端低层切换

前端底层预取调用已从真实 complete 切换为新 preview 接口：

- 原先 `prefetchConsultationSystemQuestionItem(...)` 实际调用 `/complete`
- 现在改为调用 `/preview-complete`

这一步只改低层 API 和 store action，不等同于 Step 5 的页面接入重构。

## 5. 与完成标准对照

- 新接口可独立调用：
  已满足，后端新增了独立的 `preview-complete` 路由与服务函数。
- 调用后数据库状态不变化：
  已满足，预览结果在 session 内序列化后显式 `rollback()`，不提交任何持久化修改。
- 返回值足够支持前端预热下一题视频：
  已满足，返回 payload 仍包含 `current_question_key/current_question_video_uri/current_stage/status/current_question_item` 等字段，足够前端推导下一节点视频并预热。

## 6. 本步验证

已完成的本地校验：

- `python -m compileall app`（`services/consultation-service`）
- `npm run typecheck`（`apps/consultation/client`）

尚未完成的运行时验证：

- 未在真实数据库/接口联调环境下手动调用 `preview-complete` 比对调用前后数据库状态
- 未在页面中完成 Step 5 的正式接入验证
