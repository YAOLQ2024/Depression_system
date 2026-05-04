# Multimodal Service

`multimodal-service` 当前处于协作骨架阶段，已统一为：

- PostgreSQL
- SQLAlchemy
- Alembic migration
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口

当前已实现：

- `GET /health/live`
- `GET /health/ready`

当前尚未实现业务接口，后续将承接：

- 多模态采集任务
- 特征结果落库
- 标准化 feature bundle 输出

关键环境变量：

- `DATABASE_URL`
- `MINIO_ENDPOINT`
- `MULTIMODAL_BUCKET`
