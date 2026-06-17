# Intervention Service

`intervention-service` 当前处于协作骨架阶段，已统一为：

- PostgreSQL
- SQLAlchemy
- Alembic migration
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口

当前已实现：

- `GET /health/live`
- `GET /health/ready`

当前尚未实现业务接口，后续将承接：

- 干预计划生成
- 干预执行记录
- 用户反馈回传

当前已补齐的最小执行记录链路：

- `POST /api/v1/interventions/sessions`
- `GET /api/v1/interventions/sessions/{session_id}`
- `GET /api/v1/interventions/sessions/{session_id}/events`
- `POST /api/v1/interventions/sessions/{session_id}/events`

当前前端接入规则：

- 从结果页进入调节干预时，执行会话会绑定 `consultation_session_id`
- 从首页直接进入调节干预时，不绑定问诊会话 id
- 视频 / 游戏 / 故事页面会继续复用同一个 `intervention_session`

关键环境变量：

- `DATABASE_URL`
- `WORKFLOW_RESOURCES_DIR`
- `INTERVENTION_CATALOG_DIR`
