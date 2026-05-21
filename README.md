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

- [CONTRIBUTING.md](./CONTRIBUTING.md)

## 本地运行

以下命令默认都在仓库根目录 `depression-system/` 下执行。

最常用的是下面这几条。

### 1. 默认启动

整套开发环境重建并启动：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

### 2. 只让 multimodal-service 用 GPU

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build multimodal-service
```

如果镜像已经 build 过，只重启 GPU 版：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d multimodal-service
```

### 3. 只重建某个服务

重建前端：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation
```

重建多模态服务（CPU）：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build multimodal-service
```

### 4. 看状态和日志

查看容器状态：

```bash
docker compose -f infra/compose/docker-compose.dev.yml ps
```

查看日志：

```bash
docker compose -f infra/compose/docker-compose.dev.yml logs -f consultation
docker compose -f infra/compose/docker-compose.dev.yml logs -f gateway-service
docker compose -f infra/compose/docker-compose.dev.yml logs -f multimodal-service
```

### 5. 停止环境

```bash
docker compose -f infra/compose/docker-compose.dev.yml down
```

### 6. multimodal-service 构建说明

`multimodal-service` 已拆成分层依赖，第一次 build 仍然会慢；后续如果只改 `app/` 代码，再执行：

```bash
docker compose -f infra/compose/docker-compose.dev.yml build multimodal-service
```

预期会看到 `requirements-heavy.txt` 和 `requirements-app.txt` 对应层命中 `CACHED`。

## 主要文档

- [mcs_system_blueprint_v1.md](./docs/mcs_system_blueprint_v1.md)
- [docs/services/README.md](./docs/services/README.md)
- [docs/apps/README.md](./docs/apps/README.md)
