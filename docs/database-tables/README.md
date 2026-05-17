# 数据库表说明总览

本目录用于集中说明 `depression-system` 当前已经落地到数据库的业务数据表。整理依据来自以下位置：

- 各服务的 Alembic 迁移文件
- 各服务的 SQLAlchemy 模型
- `docs/services/*/flow.md` 与 `api-and-data.md`
- 关键服务实现代码中的实际读写逻辑

截至当前代码状态，项目里真正定义了业务表的服务只有 3 个：

- `identity-service`
- `consultation-service`
- `assessment-service`

当前共有 7 张表：

| 服务 | 数据表 | 说明文件 |
| --- | --- | --- |
| `identity-service` | `users` | [users.md](./users.md) |
| `identity-service` | `sessions` | [sessions.md](./sessions.md) |
| `consultation-service` | `consultation_sessions` | [consultation_sessions.md](./consultation_sessions.md) |
| `consultation-service` | `consultation_turns` | [consultation_turns.md](./consultation_turns.md) |
| `assessment-service` | `assessment_sessions` | [assessment_sessions.md](./assessment_sessions.md) |
| `assessment-service` | `assessment_answers` | [assessment_answers.md](./assessment_answers.md) |
| `assessment-service` | `assessment_results` | [assessment_results.md](./assessment_results.md) |

补充说明：

- 本目录描述的是“当前有效表结构”，不是历史上出现过的所有字段。
- 例如 `users` 表曾短暂出现过 `family_history`，但已经在后续迁移中删除，因此不再纳入当前字段清单。
- `ai-service`、`gateway-service`、`risk-service`、`followup-service`、`intervention-service`、`multimodal-service`、`apps/operations-console/server` 目前只有服务骨架或基线迁移，还没有实际业务表定义。
