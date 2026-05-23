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

### 1. Compose 文件关系

当前仓库里，日常开发只需要理解这两个 compose 文件：

- `infra/compose/docker-compose.dev.yml`
  - 基础开发环境
  - 定义了前端、网关、业务服务、数据库、对象存储等完整本地运行骨架
  - 日常启动时必须带上它
- `infra/compose/docker-compose.gpu.yml`
  - GPU 覆盖层
  - 只覆盖 `multimodal-service` 的运行方式，例如 `runtime: nvidia`、`gpus: all`、`ASR_DEVICE=cuda`
  - 不能单独使用，必须叠加在 `docker-compose.dev.yml` 之后

它们不会冲突，原因是：

- `docker-compose.dev.yml` 提供完整服务定义
- `docker-compose.gpu.yml` 只补充或覆盖 `multimodal-service` 的少数字段
- 正确写法是“基础 compose 在前，覆盖 compose 在后”

也就是说：

- CPU 开发环境：只用 `docker-compose.dev.yml`
- GPU 开发环境：`docker-compose.dev.yml + docker-compose.gpu.yml`

### 2. 默认启动

整套开发环境重建并启动：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

### 3. GPU 模式启动

如果当前机器有可用 NVIDIA GPU，并且只想让 `multimodal-service` 走 GPU，正确命令是：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build multimodal-service
```

如果你同时改了多模态后端、问诊后端和前端页面，推荐直接重建这 3 个服务：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build multimodal-service consultation-service consultation
```

如果镜像已经 build 过，只需要用 GPU 配置重启 `multimodal-service`：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d multimodal-service
```

### 4. 只重建某个服务

重建前端：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation
```

重建多模态服务（CPU）：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build multimodal-service
```

重建问诊链路里最常动的 3 个服务：

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation consultation-service gateway-service
```

说明：

- 普通代码改动通常不需要全量重建 `postgres`、`redis`、`minio`
- 只重建你实际改到的服务即可
- 如果 `multimodal-service` 需要 GPU，就在同一条命令里继续叠加 `-f infra/compose/docker-compose.gpu.yml`

### 5. 局域网 HTTPS 启动

如果当前机器需要通过 HTTPS 给本机或同一局域网内其它设备测试摄像头、麦克风、语音和视觉模态，使用：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build consultation gateway-service caddy
```

如果当前机器还要让 `multimodal-service` 走 GPU，可继续叠加 GPU override：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build multimodal-service consultation-service consultation gateway-service caddy
```

说明：

- `docker-compose.lan-https.yml` 不是独立环境，它是 HTTPS 覆盖层
- 使用时必须和 `docker-compose.dev.yml` 一起叠加
- 证书生成方式见 [docs/architecture/lan-https-testing-plan.md](./docs/architecture/lan-https-testing-plan.md)

### 6. 看状态和日志

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

如果当前是 GPU 模式，查看 `multimodal-service` 状态或日志时，也建议继续带上 GPU override：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml ps
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml logs -f multimodal-service
```

如果当前是 LAN HTTPS 模式，也可以带上 HTTPS override 查看：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml ps
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml logs -f caddy
```

### 7. 停止环境

```bash
docker compose -f infra/compose/docker-compose.dev.yml down
```

如果当前是 GPU 模式，停止时也建议沿用相同的 compose 组合：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml down
```

如果当前是 LAN HTTPS 模式，停止时建议沿用相同的 compose 组合：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml down
```

### 8. multimodal-service 构建说明

`multimodal-service` 已拆成分层依赖，第一次 build 仍然会慢；后续如果只改 `app/` 代码，再执行：

```bash
docker compose -f infra/compose/docker-compose.dev.yml build multimodal-service
```

预期会看到 `requirements-heavy.txt` 和 `requirements-app.txt` 对应层命中 `CACHED`。

如果当前机器是 GPU 环境，正常情况下也不需要专门“重建到 heavy 依赖层”；只要：

- 没改 `Dockerfile`
- 没改 `requirements-heavy.txt`
- 没改 CUDA / ONNX / MediaPipe 底层依赖

那么直接执行前面的 `up -d --build ...` 即可，Docker 会自动复用缓存层。

### 9. face 模态最小回归

如果要快速复验 `face` 模态当前是否仍保持“基本走通”，可以从仓库根目录执行：

```powershell
.\scripts\run_face_modality_checks.ps1 -PythonExe "C:\path\to\python.exe"
```

这会顺序运行：

- `multimodal-service` 路由 smoke test
- `multimodal-service` face 服务层回归
- `consultation-service` face bundle 缓存回归

注意：

- 需要 `Python 3.11+`
- 这是分服务的最小回归包，不等于真实 DB / MinIO / 模型资源都在线时的全链路联调

## 主要文档

- [mcs_system_blueprint_v1.md](./docs/mcs_system_blueprint_v1.md)
- [docs/services/README.md](./docs/services/README.md)
- [docs/apps/README.md](./docs/apps/README.md)
