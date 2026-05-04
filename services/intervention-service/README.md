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

关键环境变量：

- `DATABASE_URL`
- `WORKFLOW_RESOURCES_DIR`
- `INTERVENTION_CATALOG_DIR`
