<div align="center">

# MCS · Multimodal Consultation System

### 面向抑郁症筛查、临床决策与个性化干预的多模态问诊系统

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/React-TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=111111" alt="React + TypeScript" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Docker_Compose-v2-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose v2" />
  <img src="https://img.shields.io/badge/PostgreSQL-Alembic-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL + Alembic" />
</p>

<p>
  <a href="#快速开始">快速开始</a> ·
  <a href="#系统概览">系统概览</a> ·
  <a href="#开发文档">开发文档</a> ·
  <a href="./CONTRIBUTING.md">协作规范</a>
</p>

</div>

---

## 项目简介

MCS 是一套服务于抑郁症筛查与干预场景的多模态问诊系统。它将数字人问诊、语音 / 视觉 / EEG 信号采集、量表评估、临床决策与个性化调节干预串成可追踪的业务闭环。

```text
患者登录 → 问诊准备 → 数字人交互问诊 → 多模态采集 → 量表评估
                                              ↓
回顾与再评估 ← 个性化调节干预 ← 临床决策 ← 风险评估
```

> 当前仓库优先提供适合多人协作的统一工程骨架：统一的运行入口、数据规范和文档边界已经就绪；部分服务尚处于业务能力持续完善阶段。

## 目录

- [系统概览](#系统概览)
- [核心能力与当前状态](#核心能力与当前状态)
- [技术栈](#技术栈)
- [仓库结构](#仓库结构)
- [快速开始](#快速开始)
- [进阶运行场景](#进阶运行场景)
- [协作约定](#协作约定)
- [开发文档](#开发文档)

## 系统概览

| 阶段 | 主要能力 | 系统支撑 |
| :-- | :-- | :-- |
| 问诊前 | 登录、身份识别、问诊准备 | `identity-service`、`gateway-service` |
| 问诊中 | 数字人交互、语音 / 视觉 / EEG 采集 | `consultation`、`consultation-service`、`multimodal-service` |
| 评估决策 | 量表评估、风险识别、临床决策 | `assessment-service`、`risk-service` |
| 干预随访 | 个性化调节、回顾与再评估 | `intervention-service`、`followup-service` |
| 运营管理 | 配置与业务运营 | `operations-console` |

## 核心能力与当前状态

### 已可用的主链

| 模块 | 作用 |
| :-- | :-- |
| `consultation` | 患者问诊前端 |
| `operations-console` | 运营管理前端 |
| `gateway-service` | 统一网关与访问入口 |
| `identity-service` | 身份与认证能力 |
| `consultation-service` | 问诊流程编排与业务服务 |

### 已统一为协作骨架的服务

`assessment-service`、`risk-service`、`intervention-service`、`followup-service`、`multimodal-service` 与 `ai-service` 均已具备统一的：

- 服务目录与启动脚本
- PostgreSQL 配置
- Alembic baseline migration
- 健康检查入口

这些服务适合并行接手开发；完整业务能力会随各模块迭代逐步补齐。

## 技术栈

| 层级 | 技术选型 |
| :-- | :-- |
| 前端 | React、TypeScript、Tailwind CSS、Vite |
| 后端 | Python 3.11+、FastAPI |
| 数据库 | PostgreSQL、Alembic、SQLAlchemy |
| 缓存与对象存储 | Redis、MinIO |
| 代理与 HTTPS | Caddy（局域网 HTTPS）、Nginx |
| 基础设施 | Docker Compose v2 |

## 仓库结构

```text
depression-system/
├── apps/                 # consultation、operations-console 等前端应用
├── services/             # 核心后端服务
├── packages/             # 共享运行资源与共享包
├── infra/                # Compose、环境模板、证书目录
├── docs/                 # 系统蓝图、服务设计、应用设计、运维说明
├── scripts/              # 本地辅助脚本（含 EEG 工具启动入口）
└── tools/                # 工具与数据资源
```

---

## 快速开始

以下命令均默认在仓库根目录 `depression-system/` 中执行。

### 1. 环境要求

- **Docker 24+** 与 **Docker Compose v2**
- 可选：**NVIDIA Container Toolkit**（运行 GPU 模式的 `multimodal-service`）
- 可选：**mkcert**（局域网 HTTPS，使浏览器可使用摄像头、麦克风等安全上下文 API）
- 可选：**Python 3.11+**（仅在需要运行 `face` 模态最小回归时使用）

### 2. 启动默认开发环境

```powershell
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

启动完成后，检查容器与主链健康状态：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml ps
curl http://localhost:8080/health/live
curl http://localhost:8000/health/live
```

### 3. 常用命令速查

| 目标 | 命令 |
| :-- | :-- |
| 启动默认 CPU + HTTP 环境 | `docker compose -f infra/compose/docker-compose.dev.yml up -d --build` |
| 查看容器状态 | `docker compose -f infra/compose/docker-compose.dev.yml ps` |
| 查看问诊前端日志 | `docker compose -f infra/compose/docker-compose.dev.yml logs -f consultation` |
| 查看网关日志 | `docker compose -f infra/compose/docker-compose.dev.yml logs -f gateway-service` |
| 停止环境 | `docker compose -f infra/compose/docker-compose.dev.yml down` |

---

## 进阶运行场景

### Compose 组合关系

基础 Compose 文件始终需要最先加载；GPU 与局域网 HTTPS 文件均为可单独或同时叠加的 override 层。

| 文件 | 用途 | 是否可单独运行 |
| :-- | :-- | :-- |
| `infra/compose/docker-compose.dev.yml` | 完整本地开发环境 | 可以，且为基础层 |
| `infra/compose/docker-compose.gpu.yml` | 为 `multimodal-service` 启用 NVIDIA / CUDA 运行配置 | 不可以 |
| `infra/compose/docker-compose.lan-https.yml` | 通过 Caddy 提供局域网 HTTPS | 不可以 |

> 使用 override 时，务必把基础文件放在前面：`-f docker-compose.dev.yml -f docker-compose.<override>.yml`。

### 四种启动组合

| 场景 | 启动命令 |
| :-- | :-- |
| CPU + HTTP（默认） | `docker compose -f infra/compose/docker-compose.dev.yml up -d --build` |
| GPU + HTTP | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build` |
| CPU + HTTPS | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build` |
| GPU + HTTPS | `docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build` |

<details>
<summary><b>局域网 HTTPS：首次证书配置</b></summary>

<br />

证书文件 `infra/certs/lan-cert.pem` 与 `infra/certs/lan-key.pem` 已加入 `.gitignore`，每台机器首次使用 HTTPS 模式时均需自行生成；缺少证书会导致 Caddy 启动失败。

```powershell
# 1. 安装 mkcert（Windows）
winget install FiloSottile.mkcert

# 2. 安装本地 CA（需要管理员权限）
mkcert -install

# 3. 生成本机证书；将 <你的局域网IP> 替换为实际地址
mkcert -cert-file infra/certs/lan-cert.pem -key-file infra/certs/lan-key.pem localhost 127.0.0.1 ::1 <你的局域网IP>
```

验证证书：

```powershell
ls infra/certs/lan-cert.pem
ls infra/certs/lan-key.pem
```

若手机或平板要通过 HTTPS 访问当前机器，还需在该设备上信任此本地 CA。详见 [LAN HTTPS 测试方案](./docs/architecture/lan-https-testing-plan.md)。

</details>

### 只重建改动的服务

日常开发无需因普通代码改动重建 `postgres`、`redis` 或 `minio`。按实际改动范围重建即可：

```powershell
# 前端
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation

# 多模态服务（CPU）
docker compose -f infra/compose/docker-compose.dev.yml up -d --build multimodal-service

# 问诊常用三层链路
docker compose -f infra/compose/docker-compose.dev.yml up -d --build consultation consultation-service gateway-service
```

若该服务需要 GPU 或 HTTPS，请在同一命令中继续叠加相应的 `-f` 文件。

<details>
<summary><b>GPU 与 HTTPS 场景的重建、日志和停止</b></summary>

<br />

```powershell
# GPU：重建多模态 + 问诊三层链路
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml up -d --build multimodal-service consultation-service consultation

# CPU + HTTPS：重建 HTTPS 链路
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml up -d --build consultation gateway-service caddy

# GPU + HTTPS：重建多模态、问诊与 HTTPS 链路
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml -f infra/compose/docker-compose.lan-https.yml up -d --build multimodal-service consultation-service consultation gateway-service caddy

# GPU 模式下查看多模态服务状态或日志
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml ps
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml logs -f multimodal-service

# HTTPS 模式下查看 Caddy 日志
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.lan-https.yml logs -f caddy

# 停止时沿用当前的 Compose 文件组合，例如 GPU 模式：
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.gpu.yml down
```

</details>

### Windows EEG 启动

前端显示 EEG 波形时，除 Docker 业务主链外，还必须启动一个 EEG 数据源。先启动默认主链：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml up -d --build
```

随后选择一种数据源：

| 数据源 | 命令 |
| :-- | :-- |
| 真机脑电帽 | `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge` |
| 模拟数据 | `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode simulate` |
| 录制文件回放 | `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode raw -ReplayFile E:\DataSets\Projects\depression-system\tools\eeg-tools\data\records\eeg-host-bridge-20260608T125403Z.jsonl -Speed 1.0` |

如果已打包单用途 EXE，也可直接启动真机桥接：

```powershell
.\eeg-bridge.exe
```

> 不要同时运行 `bridge` 与 `replay`。EEG 波形会在进入真正作答窗口后开始显示，而非一进入页面即出现。

### multimodal-service 构建说明

服务已拆分为分层依赖。首次构建仍可能较慢；后续仅修改 `app/` 代码时，可执行：

```powershell
docker compose -f infra/compose/docker-compose.dev.yml build multimodal-service
```

若没有修改 `Dockerfile`、`requirements-heavy.txt`、CUDA / ONNX / MediaPipe 等底层依赖，Docker 会复用 `requirements-heavy.txt` 与 `requirements-app.txt` 的缓存层。

### face 模态最小回归

历史的一键检查脚本已移除。如需恢复该能力，应以当前保留的测试文件重新整理回归入口，而不是继续使用失效的历史脚本。

- 需要 Python 3.11+
- 该回归包为分服务的最小检查，不等同于真实 DB、MinIO、模型资源均在线时的端到端联调

---

## 协作约定

开始编码前，请先阅读对应模块文档：

- 服务：`docs/services/<service-name>/`
- 应用：`docs/apps/<app-name>/`

数据库开发须遵守以下边界：

- 统一使用 PostgreSQL，不使用 SQLite
- 表结构统一由 Alembic 管理
- 运行期读写统一使用 SQLAlchemy
- 禁止通过字符串拼接构造 SQL

完整的开发顺序、服务约定和提交自检要求见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 开发文档

| 面向对象 | 文档 |
| :-- | :-- |
| 新成员 | [系统蓝图 V1](./docs/mcs_system_blueprint_v1.md) · 产品流程与架构决策 |
| 服务开发者 | [服务文档总览](./docs/services/README.md) · overview / api-and-data / flow / tasks |
| 前端开发者 | [应用文档总览](./docs/apps/README.md) · overview / api-and-data / flow / tasks |
| 运维与环境 | [Phase B 运维手册](./docs/operations/phase-b-runbook.md) |
| 局域网设备联调 | [LAN HTTPS 测试方案](./docs/architecture/lan-https-testing-plan.md) |

---

<div align="center">

持续完善多模态心理健康服务的工程基础。欢迎通过规范的分支、文档与提交记录共同协作。

</div>
