# Consultation Service

`consultation-service` 是规则版数字人问诊主链服务。

当前已实现：

- PostgreSQL + Alembic migration
- `consultation_sessions` / `consultation_turns` 两张核心表
- workflow / interview script 资源装载
- digital human playlist manifest 装载
- 四段规则问诊的最小状态机骨架
- 会话创建、启动、获取状态、提交一轮输入

当前接口：

- `GET /health/live`
- `GET /health/ready`
- `POST /api/v1/consultations`
- `GET /api/v1/consultations/{session_id}`
- `POST /api/v1/consultations/{session_id}/start`
- `POST /api/v1/consultations/{session_id}/turns`

当前已接入的多模态协作能力：

- 语音上传后接收 `speech/text` 结果
- `face/pose` capture 转发到 `multimodal-service`
- 当前轮 `turn_bundle` 缓存到 `consultation_turn.turn_summary_payload`

## Face 相关回归

当前仓库已经补了 `face` 相关的 consultation 层单元测试，重点验证：

- 有 `turn_id` 时会缓存上游返回的 `turn_bundle`
- 无 `turn_id` 时不会误写 turn 缓存

统一复验命令建议从仓库根目录执行：

```powershell
.\scripts\run_face_modality_checks.ps1 -PythonExe "C:\path\to\python.exe"
```

启动方式：

- 容器启动先执行 `alembic upgrade head`
- 然后再启动 `uvicorn`
