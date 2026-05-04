# Assessment Service

`assessment-service` 当前处于协作骨架阶段，已统一为：

- PostgreSQL
- SQLAlchemy
- Alembic migration
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口

当前已实现：

- `GET /health/live`
- `GET /health/ready`

当前尚未实现业务接口，后续将承接：

- 4 个量表会话创建
- 逐题作答
- 计分与聚合结果
- `assessment_aggregate_payload` 输出

关键环境变量：

- `DATABASE_URL`
- `WORKFLOW_RESOURCES_DIR`
- `ACTIVE_SCALE_SET`
