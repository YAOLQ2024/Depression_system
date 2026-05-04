# Followup Service

`followup-service` 当前处于协作骨架阶段，已统一为：

- PostgreSQL
- SQLAlchemy
- Alembic migration
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口

当前已实现：

- `GET /health/live`
- `GET /health/ready`

当前尚未实现业务接口，后续将承接：

- 对话回顾记录
- 时间线与导出
- 再评估任务管理

关键环境变量：

- `DATABASE_URL`
- `REPORT_EXPORT_DIR`
