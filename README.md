# MCS

`MCS` 是 `Multimodal Consultation System` 的全新研发仓库。

当前仓库目标不是“先把所有业务做完”，而是先提供一套适合多人协作的统一工程骨架：

- 2 个前端应用
- 8 个核心服务
- 1 个可选 `ai-service`
- 统一的 Postgres + Alembic + SQLAlchemy 规范
- 统一的 Docker Compose 本地开发入口
- 统一的文档驱动开发方式

## 当前状态

已经可用的主链：

- `consultation`
- `operations-console`
- `gateway-service`
- `identity-service`
- `consultation-service`

已经统一成正式协作骨架的服务：

- `assessment-service`
- `risk-service`
- `intervention-service`
- `followup-service`
- `multimodal-service`
- `ai-service`

其中后 6 个服务当前主要提供：

- 标准目录结构
- Postgres 配置
- Alembic baseline migration
- 统一启动脚本
- 健康检查

它们还没有进入完整业务实现阶段，但已经适合分工接手开发。

## 仓库结构

- `apps/`
  - `consultation`
  - `operations-console`
- `services/`
  - 核心后端服务
- `packages/`
  - 共享运行资源与共享包
- `infra/`
  - compose、脚本、环境模板
- `docs/`
  - 蓝图、服务设计、应用设计、运维说明

## 协作规则

开始写代码前，先读对应文档：

- 服务：`docs/services/<service-name>/`
- 应用：`docs/apps/<app-name>/`

开发约束：

- 数据库统一使用 PostgreSQL
- 表结构统一由 Alembic 管理
- 运行期读写统一使用 SQLAlchemy
- 不再使用 SQLite
- 不允许通过字符串拼接构造 SQL

详细协作规范见：

- [CONTRIBUTING.md](/home/ZR/data2/MCS/CONTRIBUTING.md)

## 本地运行

以下命令默认都在仓库根目录 `depression-system/` 下执行。

核心链路：

```bash
make up-core
```

协作骨架全起（不含可选 AI）：

```bash
make up
```

包含可选 AI：

```bash
make up-ai
```

配置检查：

```bash
make compose-config
make phase-check
```

常用 Docker Compose 命令：

整套开发环境一行重建并启动：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

整套开发环境拆成两步：

```bash
docker compose -f infra/compose/docker-compose.dev.yml build
docker compose -f infra/compose/docker-compose.dev.yml up -d
```

只重建并启动 `consultation` 及其依赖：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation
```

只启动 `consultation` 拆成两步：

```bash
docker compose -f infra/compose/docker-compose.dev.yml build consultation
docker compose -f infra/compose/docker-compose.dev.yml up -d consultation
```

查看容器状态：

```bash
docker compose -f infra/compose/docker-compose.dev.yml ps
```

查看常用日志：

```bash
docker compose -f infra/compose/docker-compose.dev.yml logs -f consultation
docker compose -f infra/compose/docker-compose.dev.yml logs -f gateway-service
```

停止并移除当前 compose 环境：

```bash
docker compose -f infra/compose/docker-compose.dev.yml down
```

## 主要文档

- [mcs_system_blueprint_v1.md](/home/ZR/data2/MCS/docs/mcs_system_blueprint_v1.md)
- [docs/services/README.md](/home/ZR/data2/MCS/docs/services/README.md)
- [docs/apps/README.md](/home/ZR/data2/MCS/docs/apps/README.md)
