# MCS — Multimodal Consultation System（多模态问诊系统）

MCS 是一个面向抑郁症筛查与干预的**多模态问诊系统**，核心流程为：

> 患者登录 → 问诊准备 → 数字人交互问诊（语音 / 视觉 / EEG 多模态采集）→ 量表评估 → 临床决策 → 个性化调节干预 → 回顾与再评估闭环

当前仓库目标不是”先把所有业务做完”，而是先提供一套适合多人协作的统一工程骨架：

- 2 个前端应用
- 8 个核心服务
- 1 个可选 `ai-service`
- 统一的 Postgres + Alembic + SQLAlchemy 规范
- 统一的 Docker Compose 本地开发入口
- 统一的文档驱动开发方式

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React + TypeScript + TailwindCSS + Vite |
| 后端 | Python 3.11+ / FastAPI |
| 数据库 | PostgreSQL + Alembic（迁移）+ SQLAlchemy（ORM） |
| 缓存 / 对象存储 | Redis / MinIO |
| 反向代理 | Caddy（LAN HTTPS）/ Nginx |
| 基础设施 | Docker Compose v2 |

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

### 0. 前置条件

- **Docker 24+** 与 **Docker Compose v2**
- （可选）**NVIDIA Container Toolkit** — 如需 GPU 模式运行 `multimodal-service`
- （可选）**mkcert** — 如需 LAN HTTPS 模式，每台机器必须先安装 mkcert 并生成本地证书（[步骤](#https-证书一次性配置)）
- （可选）**Python 3.11+** — 仅 `face` 模态最小回归脚本需要

### 1. Compose 文件关系

当前仓库里，日常开发需要理解以下 compose 文件：

- `infra/compose/docker-compose.dev.yml`（基础环境，必须）
  - 定义了前端、网关、业务服务、数据库、对象存储等完整本地运行骨架
  - 始终作为第一个 compose 文件加载
- `infra/compose/docker-compose.gpu.yml`（GPU 覆盖层，可选）
  - 只覆盖 `multimodal-service` 的运行方式，例如 `runtime: nvidia`、`gpus: all`、`ASR_DEVICE=cuda`
  - 不能单独使用，必须叠加在 `docker-compose.dev.yml` 之后
- `infra/compose/docker-compose.lan-https.yml`（LAN HTTPS 覆盖层，可选）
  - 通过 Caddy 提供局域网 HTTPS 访问，用于测试摄像头、麦克风等需要安全上下文的浏览器 API
  - 不能单独使用，必须叠加在 `docker-compose.dev.yml` 之后
  - 证书生成方式见 [docs/architecture/lan-https-testing-plan.md](./docs/architecture/lan-https-testing-plan.md)
- `infra/compose/docker-compose.jetson-eeg-bridge.yml`（Linux 原生 BLE EEG 覆盖层，真机可选）
  - 启动 `eeg-bridge` 容器，通过宿主机 BlueZ 的 system D-Bus 原生扫描和连接 EEG 蓝牙设备
  - `multimodal-service` 通过 Redis Stream 消费 EEG 数据；即使文件名含 `jetson`，Linux 桌面环境同样使用此覆盖层
  - 使用真机 EEG 时必须叠加；不要在缺少此文件的启动命令上使用 `--remove-orphans`，以免误删正在运行的 `eeg-bridge`

各个 override 文件可以按需叠加在 `docker-compose.dev.yml` 之上：

- `docker-compose.dev.yml` 提供完整服务定义
- override 文件只补充或覆盖各自关心的少数字段
- 正确写法是”基础 compose 在前，覆盖 compose 在后”

常用组合：

- CPU 开发环境：只用 `docker-compose.dev.yml`
- GPU 开发环境：`docker-compose.dev.yml + docker-compose.gpu.yml`
- LAN HTTPS 环境：`docker-compose.dev.yml + docker-compose.lan-https.yml`
- GPU + LAN HTTPS：三个文件同时叠加
- Linux 真机 EEG：在所选组合后继续叠加 `docker-compose.jetson-eeg-bridge.yml`

### 2. HTTPS 证书一次性配置

证书文件（`infra/certs/lan-cert.pem`、`infra/certs/lan-key.pem`）已加入 `.gitignore`，不会提交到仓库。**每台机器首次使用 HTTPS 模式前，必须自行生成**，否则 Caddy 容器会因缺少证书文件启动失败。

步骤（每台机器只需做一次）：

```powershell
# 1. 安装 mkcert（Windows）
winget install FiloSottile.mkcert

# 2. 安装本地 CA（需管理员权限）
mkcert -install

# 3. 生成本机证书（把 <你的局域网IP> 替换为实际地址，如 10.101.10.121）
mkcert -cert-file infra/certs/lan-cert.pem -key-file infra/certs/lan-key.pem localhost 127.0.0.1 ::1 <你的局域网IP>
```

验证证书是否生成成功：

```powershell
ls infra/certs/lan-cert.pem
ls infra/certs/lan-key.pem
```

> 如果另一台设备（如手机、平板）要通过浏览器访问当前机器的 HTTPS 页面，还需要在那台设备上信任当前机器的本地 CA。详见 [LAN HTTPS 测试方案](./docs/architecture/lan-https-testing-plan.md)。

### 3. 启动命令速查

日常开发按是否使用 GPU、是否需要 HTTPS 选择组合；Linux 真机 EEG 再额外叠加 BLE bridge 覆盖层：

| 场景 | 命令 |
|---|---|
| CPU + HTTP（默认） | `docker compose -f infra/compose/docker-compose.dev.yml up -d --build` |
| GPU + HTTP | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build` |
| CPU + HTTPS | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build` |
| GPU + HTTPS | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build` |
| GPU + HTTPS + Linux 真机 EEG | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml -f infra/compose/docker-compose.jetson-eeg-bridge.yml up -d --build` |

> 以上命令都会重建有变更的镜像并启动全部服务。如果只想启动或重建特定服务，在末尾追加服务名即可，见 [第 5 节](#5-只重建某个服务)。

### 3.1 Windows EEG 启动速查

如果你要在前端看到 EEG 波形，除了启动 Docker 业务主链，还必须再启动一个 EEG 数据源。

先启动业务主链：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

然后三选一：

- 真机脑电帽：
  `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge`
- 模拟数据：
  `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode simulate`
- 录制文件回放：
  `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode raw -ReplayFile E:\DataSets\Projects\depression-system\tools\eeg-tools\data\records\eeg-host-bridge-20260608T125403Z.jsonl -Speed 1.0`

如果已经打包单用途 EXE，也可以直接启动真机桥接：

```powershell
.\eeg-bridge.exe
```

注意：

- 不要同时启动 `bridge` 和 `replay`
- 当前 EEG 波形不是进入页面立刻出现，而是在进入真正作答窗口后开始显示

### 3.2 Linux 原生 BLE EEG 启动

Linux 上连接真机 EEG 时，BLE 由 `eeg-bridge` 容器通过宿主机的 BlueZ / system D-Bus 原生处理；`multimodal-service` 只从 Redis Stream 消费数据。以 GPU + LAN HTTPS 为例：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build
```

确认 `eeg-bridge` 正常运行：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  ps eeg-bridge
```

### 4. 各场景完整命令

#### 4.1 默认（CPU + HTTP）

```bash
# 首次或全量重建
docker compose -f infra/compose/docker-compose.dev.yml up -d --build

# 如果镜像已 build 过，无需重建
docker compose -f infra/compose/docker-compose.dev.yml up -d
```

启动后验证：

```bash
docker compose -f infra/compose/docker-compose.dev.yml ps
curl http://localhost:8080/health/live
curl http://localhost:8000/health/live
```

#### 4.2 GPU + HTTP

```bash
# 全量重建（首次推荐）
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build

# 镜像已 build 过，只需重启
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d
```

如果只改了三层链路（多模态 + 问诊后端 + 前端），推荐只重建这 3 个服务：

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build multimodal-service consultation-service consultation
```

#### 4.3 CPU + HTTPS

适用于同一局域网内其它设备测试摄像头、麦克风、语音和视觉模态（需要安全上下文）：

```bash
# 全量重建
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build

# 只重建 HTTPS 链路（consultation + gateway + caddy）
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build consultation gateway-service caddy
```

#### 4.4 GPU + HTTPS

```bash
# 全量重建
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build

# 只重建三层链路 + HTTPS
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build multimodal-service consultation-service consultation gateway-service caddy
```

#### 4.5 日常快速启动 GPU + HTTPS + Linux 原生 BLE EEG

Jetson / Orin 或 Linux 桌面环境下，如果默认要使用 GPU 推理、让局域网设备通过 HTTPS 访问摄像头和麦克风页面，并连接真机 EEG，优先使用这一组命令。

部署排障记录见：[Jetson GPU + LAN HTTPS 部署排障记录](./docs/operations/jetson-gpu-https-deployment-troubleshooting_20260727.md)。

首次使用 HTTPS 前，先确认本目录存在证书：

```bash
ls infra/certs/lan-cert.pem infra/certs/lan-key.pem
```

如果当前目录没有证书，需要先在本机生成或从可信备份恢复 `infra/certs/lan-cert.pem` 和 `infra/certs/lan-key.pem`。例如本机已安装 `mkcert` 时：

```bash
mkdir -p infra/certs
mkcert -cert-file infra/certs/lan-cert.pem -key-file infra/certs/lan-key.pem \
  localhost 127.0.0.1 ::1 "$(hostname -I | awk '{print $1}')"
```

启动或重建 GPU + HTTPS 全链路：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build
```

如果镜像已经构建过，只想快速恢复服务：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d
```

如果只是重启已启动的容器：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  restart
```

如果只修复或重启 HTTPS 入口：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d caddy
```

查看服务状态：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  ps
```

局域网访问地址使用当前机器的局域网 IP，例如当前机器 IP 是 `10.43.33.232` 时：

- 问诊前端 HTTPS：`https://10.43.33.232`
- 问诊前端 HTTP：`http://10.43.33.232:3000`
- 运维控制台 HTTP：`http://10.43.33.232:3001`
- Gateway HTTP：`http://10.43.33.232:18080`
- Multimodal HTTP：`http://10.43.33.232:18017`
- MinIO 控制台：`http://10.43.33.232:9001`

当前机器 IP 可以用下面命令查看：

```bash
hostname -I
```

如果 `caddy` 启动后立即退出，优先检查证书是否存在：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  logs --tail=80 caddy
```

### 5. 只重建某个服务

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
- 如果需要 HTTPS，继续叠加 `-f infra/compose/docker-compose.lan-https.yml`

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

如果当前机器是 GPU 环境，正常情况下也不需要专门”重建到 heavy 依赖层”；只要：

- 没改 `Dockerfile`
- 没改 `requirements-heavy.txt`
- 没改 CUDA / ONNX / MediaPipe 底层依赖

那么直接执行前面的 `up -d --build ...` 即可，Docker 会自动复用缓存层。

### 9. face 模态最小回归

原先的人脸模态一键检查脚本已经移除。

如果后续还需要恢复这类能力，建议基于当前仍然存在的测试文件重新整理一套新的回归入口，而不是继续保留已经失效的历史脚本。

注意：

- 需要 `Python 3.11+`
- 这是分服务的最小回归包，不等于真实 DB / MinIO / 模型资源都在线时的全链路联调

## 主要文档

**新人必读：**

- [系统蓝图 V1](./docs/mcs_system_blueprint_v1.md) — 产品流程与架构决策

**服务开发者：**

- [服务文档总览](./docs/services/README.md) — 各服务的 overview / api-and-data / flow / tasks
- [协作开发约定](./CONTRIBUTING.md) — 开发顺序、服务约定、提交自检

**前端开发者：**

- [应用文档总览](./docs/apps/README.md) — 各应用的 overview / api-and-data / flow / tasks

**运维 & 环境：**

- [Phase B 运维手册](./docs/operations/phase-b-runbook.md)
- [LAN HTTPS 测试方案](./docs/architecture/lan-https-testing-plan.md)
