# AI Service

`ai-service` 当前处于协作骨架阶段，是可选扩展服务，已统一为：

- PostgreSQL
- SQLAlchemy
- Alembic migration
- `scripts/start.sh` 启动前自动迁移
- 标准健康检查接口

当前已实现：

- `GET /health/live`
- `GET /health/ready`

当前尚未实现业务接口，后续将承接：

- LLM 适配层
- 提示词编排与调用审计
- 受控 AI 增强能力

关键环境变量：

- `DATABASE_URL`
- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
