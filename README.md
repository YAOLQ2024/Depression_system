<div align="center">

# MCS · Multimodal Consultation System

### 面向抑郁症筛查、临床决策与个性化干预的多模态问诊系统

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/React-TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=111111" alt="React + TypeScript" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Docker_Compose-v2-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose v2" />
</p>

</div>

---

## 项目简介

MCS 将数字人问诊、语音 / 视觉 / EEG 信号采集、量表评估、临床决策与个性化调节干预串成可追踪的业务闭环。

```text
患者登录 → 问诊准备 → 数字人交互问诊 → 多模态采集 → 量表评估
                                              ↓
回顾与再评估 ← 个性化调节干预 ← 临床决策 ← 风险评估
```

## 系统概览

| 阶段 | 主要能力 | 系统支撑 |
| :-- | :-- | :-- |
| 问诊前 | 登录、身份识别、问诊准备 | `identity-service`、`gateway-service` |
| 问诊中 | 数字人交互、语音 / 视觉 / EEG 采集 | `consultation`、`consultation-service`、`multimodal-service` |
| 评估决策 | 量表评估、风险识别、临床决策 | `assessment-service`、`risk-service` |
| 干预随访 | 个性化调节、回顾与再评估 | `intervention-service`、`followup-service` |
| 运营管理 | 配置与业务运营 | `operations-console` |

## 技术栈

| 层级 | 技术选型 |
| :-- | :-- |
| 前端 | React、TypeScript、Tailwind CSS、Vite |
| 后端 | Python 3.11+、FastAPI |
| 数据库 | PostgreSQL、Alembic、SQLAlchemy |
| 缓存与对象存储 | Redis、MinIO |
| 代理与 HTTPS | Caddy（局域网 HTTPS）、Nginx |
| 基础设施 | Docker Compose v2 |

## 快速开始

以下命令均在仓库根目录 `depression-system/` 中执行。

### 环境要求

- **Docker 24+** 与 **Docker Compose v2**
- 可选：**NVIDIA Container Toolkit**（GPU 模式）
- 可选：**mkcert**（LAN HTTPS）
- 可选：**Python 3.11+**（`face` 模态最小回归）

### 默认开发环境

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
docker compose -f infra/compose/docker-compose.dev.yml ps
curl http://localhost:8080/health/live
curl http://localhost:8000/health/live
```

### 常用命令

| 目标 | 命令 |
| :-- | :-- |
| 启动默认 CPU + HTTP 环境 | `docker compose -f infra/compose/docker-compose.dev.yml up -d --build` |
| 查看容器状态 | `docker compose -f infra/compose/docker-compose.dev.yml ps` |
| 查看问诊前端日志 | `docker compose -f infra/compose/docker-compose.dev.yml logs -f consultation` |
| 查看网关日志 | `docker compose -f infra/compose/docker-compose.dev.yml logs -f gateway-service` |
| 停止环境 | `docker compose -f infra/compose/docker-compose.dev.yml down` |

## 进阶运行场景

### Compose 组合关系

基础 Compose 文件必须最先加载；其余文件可按需叠加。

| 文件 | 用途 | 是否可单独运行 |
| :-- | :-- | :-- |
| `infra/compose/docker-compose.dev.yml` | 完整本地开发环境 | 可以，且为基础层 |
| `infra/compose/docker-compose.gpu.yml` | 为 `multimodal-service` 启用 NVIDIA / CUDA | 不可以 |
| `infra/compose/docker-compose.lan-https.yml` | 通过 Caddy 提供局域网 HTTPS | 不可以 |
| `infra/compose/docker-compose.jetson-eeg-bridge.yml` | Linux 原生 BLE EEG bridge | 不可以 |

### 启动组合

| 场景 | 启动命令 |
| :-- | :-- |
| CPU + HTTP（默认） | `docker compose -f infra/compose/docker-compose.dev.yml up -d --build` |
| GPU + HTTP | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build` |
| CPU + HTTPS | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build` |
| GPU + HTTPS | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build` |
| GPU + HTTPS + Linux 真机 EEG | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml -f infra/compose/docker-compose.jetson-eeg-bridge.yml up -d --build` |

### HTTPS 证书

证书文件 `infra/certs/lan-cert.pem` 与 `infra/certs/lan-key.pem` 已加入 `.gitignore`。每台机器首次使用 HTTPS 模式时需自行生成；缺少证书会导致 Caddy 启动失败。

```bash
mkdir -p infra/certs
mkcert -cert-file infra/certs/lan-cert.pem -key-file infra/certs/lan-key.pem \
  localhost 127.0.0.1 ::1 "$(hostname -I | awk '{print $1}')"
```

手机或平板访问时，还需要信任当前机器的本地 CA。详见 [LAN HTTPS 测试方案](./docs/architecture/lan-https-testing-plan.md)。

### Linux 原生 BLE EEG

Linux 连接真机 EEG 时，`eeg-bridge` 容器通过宿主机 BlueZ 的 system D-Bus 扫描和连接设备，`multimodal-service` 从 Redis Stream 消费 EEG 数据。即使 Compose 文件名含 `jetson`，Linux 桌面环境同样使用它。

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build

docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  ps eeg-bridge
```

真机 EEG 运行时，不要在缺少 `docker-compose.jetson-eeg-bridge.yml` 的命令中使用 `--remove-orphans`，否则会误删正在运行的 `eeg-bridge`。

### Windows EEG

Windows 默认开发链路由宿主机 EEG 工具提供数据源：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge
```

也可使用 `replay -Mode simulate` 进行模拟数据联调；不要同时运行 `bridge` 与 `replay`。

### 只重建改动的服务

```bash
# 前端
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation

# 多模态服务（CPU）
docker compose -f infra/compose/docker-compose.dev.yml up -d --build multimodal-service

# 问诊三层链路
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation consultation-service gateway-service
```

GPU、HTTPS 或 Linux EEG 环境下，在同一条命令中继续叠加对应的 `-f` 文件。

### multimodal-service 构建说明

服务已拆分为分层依赖。首次构建可能较慢；后续仅修改 `app/` 代码时可执行：

```bash
docker compose -f infra/compose/docker-compose.dev.yml build multimodal-service
```

若未修改 `Dockerfile`、`requirements-heavy.txt`、CUDA / ONNX / MediaPipe 等底层依赖，Docker 会复用依赖缓存层。

## 协作约定

开始编码前，请先阅读对应模块文档：

- 服务：`docs/services/<service-name>/`
- 应用：`docs/apps/<app-name>/`

数据库统一使用 PostgreSQL、Alembic 与 SQLAlchemy；禁止使用 SQLite 或字符串拼接 SQL。完整协作要求见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 开发文档

| 面向对象 | 文档 |
| :-- | :-- |
| 新成员 | [系统蓝图 V1](./docs/mcs_system_blueprint_v1.md) |
| 服务开发者 | [服务文档总览](./docs/services/README.md) |
| 前端开发者 | [应用文档总览](./docs/apps/README.md) |
| 运维与环境 | [Phase B 运维手册](./docs/operations/phase-b-runbook.md) |
| Jetson Orin Nano 8 GB | [板端部署与验收](./docs/operations/jetson-orin-nano-deployment.md) |
| 局域网设备联调 | [LAN HTTPS 测试方案](./docs/architecture/lan-https-testing-plan.md) |
