# 协作开发约定

这份约定的目标很简单：让 `MCS` 可以直接进入多人协作，而不是每个人按自己的习惯各写一套。

## 1. 开发顺序

先读文档，再改代码。

对应关系：

- 应用：`docs/apps/<app-name>/`
- 服务：`docs/services/<service-name>/`

至少先看：

- `overview.md`
- `api-and-data.md`
- `flow.md`
- `tasks.md`

如果文档和代码冲突：

- 先不要私自扩散写法
- 先修正文档或补设计结论
- 再动代码

## 2. 服务约定

所有后端服务统一遵守：

- 数据库：PostgreSQL
- 迁移：Alembic
- 运行期 ORM：SQLAlchemy
- 启动方式：`scripts/start.sh`
- 健康检查：`/health/live`、`/health/ready`

禁止事项：

- 不要新引入 SQLite
- 不要通过字符串拼接构造 SQL
- 不要绕过 Alembic 直接在线改表
- 不要把本该属于别的领域服务的业务逻辑塞进当前服务

## 3. 应用约定

前端应用统一遵守：

- 浏览器只连 `gateway-service`
- 不直接请求后端领域服务
- 不在前端复制业务状态机逻辑
- 当前可以用占位实现验证链路，但正式版要按文档收敛

## 4. 分工方式

推荐按服务或应用认领，不按文件碎片认领。

推荐分工粒度：

- 一个人负责一个 service
- 或一个人负责一个 app

不要同时让多人在同一个服务里随意并行改动数据库模型、迁移文件和 API 契约。

## 5. 提交前自检

提交前至少完成：

```bash
make compose-config
make phase-check
```

如果你修改了某个服务，还应至少补做：

- 对应 Python 文件语法检查
- 对应容器可启动检查
- 对应接口基本联调

## 6. 新增功能流程

新增功能建议走这条路径：

1. 先在对应 `docs/.../tasks.md` 里确认任务边界
2. 如有必要，先更新 `overview.md / api-and-data.md / flow.md`
3. 再改代码
4. 补 migration / 配置 / README

## 7. 当前阶段建议

当前最适合并行开发的切分方式是：

- `assessment-service`
- `risk-service`
- `intervention-service`
- `followup-service`
- `multimodal-service`
- `consultation` 前端正式版

其中 `ai-service` 当前属于可选扩展，不建议优先抢做。
