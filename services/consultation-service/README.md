# Consultation Service

`consultation-service` 是规则版数字人问诊主链服务。

当前已实现：

- PostgreSQL + Alembic migration
- `consultation_sessions` / `consultation_turns` 两张核心表
- workflow / interview script 资源装载
- 四段规则问诊的最小状态机骨架
- 会话创建、启动、获取状态、提交一轮输入

当前接口：

- `GET /health/live`
- `GET /health/ready`
- `POST /api/v1/consultations`
- `GET /api/v1/consultations/{session_id}`
- `POST /api/v1/consultations/{session_id}/start`
- `POST /api/v1/consultations/{session_id}/turns`

启动方式：

- 容器启动先执行 `alembic upgrade head`
- 然后再启动 `uvicorn`
