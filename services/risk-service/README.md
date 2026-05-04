# Risk Service

`risk-service` 当前处于协作骨架阶段，已统一为：

- PostgreSQL
- SQLAlchemy
- Alembic migration
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口

当前已实现：

- `GET /health/live`
- `GET /health/ready`

当前尚未实现业务接口，后续将承接：

- 问诊结果与量表结果聚合输入
- 风险分层
- 风险解释与转介建议

关键环境变量：

- `DATABASE_URL`
- `CONSULTATION_SERVICE_URL`
- `ASSESSMENT_SERVICE_URL`
- `MULTIMODAL_SERVICE_URL`
