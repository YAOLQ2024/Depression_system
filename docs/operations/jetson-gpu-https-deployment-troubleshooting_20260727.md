# Jetson GPU + LAN HTTPS 部署排障记录（2026-07-27）

本文记录 2026-07-27 在 Jetson / Orin 板端启动 GPU + LAN HTTPS 环境时遇到的问题、定位方式和处理方案。

> 目录说明：问题最初发生在旧的 `feature/zhurui` worktree `/home/medai/depression-system-zhurui-sync`。当前已整理为单一工作区，正式使用目录为 `/home/medai/depression-system`，当前分支为 `feature/zhurui`。下方推荐命令均以当前正式目录为准；历史排障段落中出现的旧 worktree 路径仅用于说明当时的处理背景。

适用场景：

- Jetson / Orin 板端部署
- `docker-compose.dev.yml + docker-compose.gpu.yml + docker-compose.lan-https.yml`
- 局域网 HTTPS 访问问诊前端
- 多模态 warmup、数字人视频、ASR / ONNX / TensorRT 资源加载

## 1. 推荐启动命令

```bash
cd /home/medai/depression-system

docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  up -d --build
```

查看服务状态：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  ps
```

局域网访问地址使用当前机器 IP，例如：

```text
https://10.43.33.232
```

当前机器 IP：

```bash
hostname -I
```

## 2. 板端 Docker 环境来源

主分支或 zr 分支本身并不“自带 Docker 环境”。仓库提供的是：

- `infra/compose/*.yml`
- 各服务 `Dockerfile`
- 启动文档和资源目录

真正让下面命令能运行的前提，是板子系统已经安装并配置了 Docker / Compose / NVIDIA Container Toolkit：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  up -d --build
```

本次板端检查结果：

```text
Docker version 29.4.1
Docker Compose version v5.1.3
Docker runtimes: io.containerd.runc.v2 nvidia runc
Default runtime: runc
NVIDIA Container Toolkit: 1.16.2
当前用户 medai 属于 docker 组
```

系统配置文件：

```text
/etc/docker/daemon.json
```

当前内容包含 NVIDIA runtime：

```json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    }
}
```

Docker daemon 代理由 systemd 环境配置提供：

```bash
systemctl show docker --property=Environment
```

本次现场值：

```text
HTTP_PROXY=http://127.0.0.1:17897
HTTPS_PROXY=http://127.0.0.1:17897
NO_PROXY=localhost,127.0.0.1,::1
```

apt 安装历史显示板子上安装过：

```text
docker-ce
docker-ce-cli
containerd.io
docker-buildx-plugin
docker-compose-plugin
libnvidia-container1
libnvidia-container-tools
nvidia-container-toolkit-base
nvidia-container-toolkit
```

可以确认：当前板子是被系统级预配置过的 Jetson Docker 环境。仅拉下主分支代码，不足以保证另一块新板子能直接运行 GPU Docker；新板子还需要先完成 Docker、Compose、NVIDIA Container Toolkit、Docker daemon proxy、证书和 LFS 资源准备。

## 3. Docker 拉镜像失败：代理端口不一致

### 现象

构建时报错：

```text
proxyconnect tcp: dial tcp 127.0.0.1:17890: connect: connection refused
```

或：

```text
proxyconnect tcp: dial tcp 127.0.0.1:7897: connect: connection refused
```

### 原因

Docker daemon / 当前 shell 里的代理端口和真实代理监听端口不一致。

本次现场状态：

- 旧配置曾指向 `127.0.0.1:17890`
- 用户以为代理端口是 `7897`
- 实际可用 HTTP 代理监听在 `127.0.0.1:17897`

确认监听端口：

```bash
ss -ltnp | grep -E ':(17890|17897|7897)\b'
```

确认 Docker daemon 代理：

```bash
docker info | grep -i proxy -A3
systemctl show docker --property=Environment
```

确认当前 shell 代理：

```bash
env | grep -iE '^(http|https|all|no)_proxy='
```

测试代理是否能访问 Docker Hub：

```bash
curl -I --max-time 8 \
  --proxy http://127.0.0.1:17897 \
  https://registry-1.docker.io/v2/
```

正常情况下会返回 Docker Registry 的 `401` 响应；这说明网络链路是通的。

### 处理方案

把 Docker daemon 代理改成实际监听端口：

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d

sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf >/dev/null <<'EOF'
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:17897"
Environment="HTTPS_PROXY=http://127.0.0.1:17897"
Environment="NO_PROXY=localhost,127.0.0.1,::1"
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

当前 shell 也应同步：

```bash
export HTTP_PROXY=http://127.0.0.1:17897
export HTTPS_PROXY=http://127.0.0.1:17897
export ALL_PROXY=http://127.0.0.1:17897
export http_proxy=http://127.0.0.1:17897
export https_proxy=http://127.0.0.1:17897
export all_proxy=http://127.0.0.1:17897
export NO_PROXY=localhost,127.0.0.1,::1
export no_proxy=localhost,127.0.0.1,::1
```

如果不想改当前 shell，也可以只对单次构建显式覆盖代理：

```bash
HTTP_PROXY=http://127.0.0.1:17897 \
HTTPS_PROXY=http://127.0.0.1:17897 \
ALL_PROXY=http://127.0.0.1:17897 \
http_proxy=http://127.0.0.1:17897 \
https_proxy=http://127.0.0.1:17897 \
all_proxy=http://127.0.0.1:17897 \
NO_PROXY=localhost,127.0.0.1,::1 \
no_proxy=localhost,127.0.0.1,::1 \
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  up -d --build
```

## 4. Caddy HTTPS 启动失败：缺少证书

### 现象

`caddy` 容器退出：

```text
open /certs/lan-cert.pem: no such file or directory
```

查看日志：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  logs --tail=80 caddy
```

### 原因

`infra/certs/lan-cert.pem` 和 `infra/certs/lan-key.pem` 被 `.gitignore` 忽略，不会随仓库提交。每个 worktree / 每台机器需要自行准备。

### 处理方案

如果主 worktree 已有证书，可以复制：

```bash
cd /home/medai/depression-system-zhurui-sync

cp /home/medai/depression-system/infra/certs/lan-cert.pem infra/certs/lan-cert.pem
cp /home/medai/depression-system/infra/certs/lan-key.pem infra/certs/lan-key.pem
```

然后启动或重启 Caddy：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  up -d caddy
```

## 5. warmup 接口 500：ONNX / ASR 模型是 Git LFS 指针

### 现象

浏览器控制台：

```text
POST https://<局域网IP>/api/v1/multimodal/sessions/<id>/warmup 500
```

`multimodal-service` 日志：

```text
INVALID_PROTOBUF : Load model from /app/runtime-assets/models/text_emotion/model.onnx failed: Protobuf parsing failed.
```

### 原因

zr worktree 中的模型文件不是实际模型，而是 Git LFS 指针文件，通常只有 132–134 字节。

检查方式：

```bash
find services/multimodal-service/runtime-assets \
  -maxdepth 4 \
  -type f \( -name '*.onnx' -o -name '*.pt' -o -name '*.plan' \) \
  -printf '%s\t%p\n' \
  | sort -n
```

如果看到类似下面的大小，就是 LFS 指针，不是真模型：

```text
132 services/multimodal-service/runtime-assets/models/pose_emotion/model.onnx
134 services/multimodal-service/runtime-assets/models/text_emotion/model.onnx
134 services/multimodal-service/runtime-assets/asr/base.cn.streaming/base.cn.streaming.pt
```

### 处理方案

当前机器没有 `git lfs`，本次直接从主 worktree 复制真实模型资源：

```bash
cd /home/medai/depression-system-zhurui-sync

cp /home/medai/depression-system/services/multimodal-service/runtime-assets/asr/base.cn.streaming/base.cn.streaming.pt \
   services/multimodal-service/runtime-assets/asr/base.cn.streaming/base.cn.streaming.pt

cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/audio_emotion/model.onnx \
   services/multimodal-service/runtime-assets/models/audio_emotion/model.onnx
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/face_emotion/model.onnx \
   services/multimodal-service/runtime-assets/models/face_emotion/model.onnx
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/pose_emotion/model.onnx \
   services/multimodal-service/runtime-assets/models/pose_emotion/model.onnx
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/text_emotion/model.onnx \
   services/multimodal-service/runtime-assets/models/text_emotion/model.onnx
```

如果要启用 TensorRT 加速路径，也复制 `.plan`：

```bash
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/audio_emotion/model.plan \
   services/multimodal-service/runtime-assets/models/audio_emotion/model.plan
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/face_emotion/model.plan \
   services/multimodal-service/runtime-assets/models/face_emotion/model.plan
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/pose_emotion/model.plan \
   services/multimodal-service/runtime-assets/models/pose_emotion/model.plan
cp /home/medai/depression-system/services/multimodal-service/runtime-assets/models/text_emotion/model.plan \
   services/multimodal-service/runtime-assets/models/text_emotion/model.plan
```

重启多模态服务：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  restart multimodal-service
```

## 6. warmup 接口 500：Jetson GPU 镜像缺少 torchaudio

### 现象

补齐 ONNX / ASR 文件后，warmup 仍然返回 500。

`multimodal-service` 日志：

```text
DolphinAsrError: failed to import dolphin runtime: No module named 'torchaudio'
```

容器内确认：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  exec -T multimodal-service python - <<'PY'
for name in ["torch", "torchaudio", "dolphin"]:
    try:
        m = __import__(name)
        print(name, getattr(m, "__version__", "ok"))
    except Exception as exc:
        print(name, "ERR", repr(exc))
PY
```

### 原因

`docker-compose.gpu.yml` 使用 NVIDIA Jetson PyTorch 基础镜像：

```text
nvcr.io/nvidia/pytorch:25.06-py3-igpu
```

该镜像包含 NVIDIA 定制版 `torch`，但现场没有 `torchaudio`。

原 Dockerfile 在 `JETSON_GPU_ENABLED=true` 时会删掉 `torch` 和 `torchaudio`，避免 pip 替换 NVIDIA 定制版 `torch`。这导致 `torchaudio` 也没有被安装。

### 永久修复

已修改 `services/multimodal-service/Dockerfile`：

- 保留 NVIDIA 镜像自带 `torch`
- 检查 `torchaudio`
- 如果缺失，执行 `pip install --no-deps torchaudio==2.8.0`
- 使用 `--no-deps`，避免 pip 重新解析并替换 NVIDIA 定制版 `torch`

核心逻辑：

```dockerfile
ARG JETSON_TORCHAUDIO_VERSION=2.8.0

RUN --mount=type=cache,id=multimodal-pip-heavy,target=/root/.cache/pip \
    ... \
    pip install -r requirements-heavy.platform.txt; \
    if [ "$JETSON_GPU_ENABLED" = "true" ]; then \
        python -c "import torchaudio" || pip install --no-deps "torchaudio==${JETSON_TORCHAUDIO_VERSION}"; \
    fi
```

重建：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  up -d --build multimodal-service
```

本次验证结果：

```text
torch      2.8.0a0+5228986c39.nv25.06
torchaudio 2.8.0
dolphin    20260513
```

## 7. 数字人视频加载失败：webm 文件是 LFS 指针

### 现象

页面显示：

```text
视频加载失败
```

zr worktree 中数字人 `.webm` 文件只有 131/132 字节。

检查方式：

```bash
find apps/consultation/client/public/digital-human \
  -type f \
  -name '*.webm' \
  -size -1024c \
  -printf '%P\t%s bytes\n'
```

### 原因

数字人视频文件同样是 Git LFS 资源，zr worktree 中是指针文件，不是真视频。

### 处理方案

从主 worktree 复制真实视频资源：

```bash
cd /home/medai/depression-system-zhurui-sync

cp -a /home/medai/depression-system/apps/consultation/client/public/digital-human/. \
      apps/consultation/client/public/digital-human/
```

因为前端静态资源会被打进 `consultation` 镜像，所以复制后必须重建前端容器：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  up -d --build consultation
```

验证容器内视频资源：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  exec -T consultation sh -lc '
    find /app/client/dist/digital-human \
      -type f \
      -name "*.webm" \
      -size -1024c \
      -printf "%P\t%s bytes\n"
    du -sh /app/client/dist/digital-human
  '
```

本次修复后：

```text
/app/client/dist/digital-human 127M
小于 1KB 的 .webm 数量为 0
```

验证 HTTPS 视频访问：

```bash
curl --noproxy '*' -k \
  https://10.43.33.232/digital-human/consultation-v1/greeting-001.webm \
  -o /tmp/greeting-001.webm

file /tmp/greeting-001.webm
```

预期：

```text
WebM
```

## 8. 板端资源检查

本次检查结果：

```text
RAM 总量:   15.6GB
当前占用:   约 4.7GB
Swap:       7.6GB，基本未使用
磁盘剩余:   约 161GB
模型资源:   约 1.7GB
数字人视频: 约 127MB
```

常用检查命令：

```bash
free -h
swapon --show
df -h /home/medai /var/lib/docker /tmp
docker stats --no-stream
timeout 4s tegrastats
```

结论：当前 16GB Orin 环境足够承载这次模型和视频资源复制，以及基础 warmup 验证。

## 9. 验证 warmup 是否恢复

创建测试多模态 session：

```bash
curl --noproxy '*' -sS -i \
  -X POST http://localhost:18017/api/v1/multimodal/sessions \
  -H 'Content-Type: application/json' \
  -H 'X-MCS-User-ID: smoke-user' \
  --data '{
    "scope_type":"encounter",
    "scope_id":"smoke-encounter",
    "encounter_session_id":"smoke-encounter"
  }'
```

调用 warmup：

```bash
curl --noproxy '*' -sS -i \
  -X POST http://localhost:18017/api/v1/multimodal/sessions/<session_id>/warmup \
  -H 'Content-Type: application/json' \
  -H 'X-MCS-User-ID: smoke-user' \
  --data '{"modalities":["text","audio","face","pose","eeg"]}'
```

本次修复后返回：

```text
HTTP/1.1 200 OK
```

## 10. 交互静态数据、动态数据的存储与查询

当前系统的数据来源可以分为四类：

1. 静态交互配置：仓库内 YAML / 静态资源文件。
2. 动态业务数据：PostgreSQL。
3. 音频、采集文件等大对象：MinIO。
4. 实时热状态：Redis。

### 静态交互配置

静态交互数据主要位于：

```text
packages/workflow-resources/
```

典型内容包括：

```text
packages/workflow-resources/workflows/consultation-v1.yaml
packages/workflow-resources/doctor-personas/*.yaml
packages/workflow-resources/interview-scripts/rule-v1/*.yaml
packages/workflow-resources/digital-human-playlists/*.yaml
packages/workflow-resources/scales/*.yaml
packages/workflow-resources/risk-rules/consultation-v1.yaml
packages/workflow-resources/intervention-programs/catalog.yaml
```

这些文件定义问诊流程、医生人设、问诊脚本、数字人播放清单、量表题目、风险规则和干预方案。Compose 启动时会把它们只读挂载进相关服务：

```text
WORKFLOW_RESOURCES_DIR=/app/workflow-resources
```

数字人视频文件位于：

```text
apps/consultation/client/public/digital-human/
```

页面通过静态路径访问，例如：

```text
https://10.43.33.232/digital-human/consultation-v1/greeting-001.webm
```

多模态模型、ASR 模型和 TensorRT plan 文件位于：

```text
services/multimodal-service/runtime-assets/
```

这类文件参与容器构建和运行时推理，不属于普通业务数据。

### 动态业务数据

动态交互数据主要存储在 PostgreSQL 中。开发 Compose 中的连接信息为：

```text
postgresql://mcs:mcs@postgres:5432/mcs
```

PostgreSQL 数据通过 Docker volume 持久化：

```text
postgres_data
```

正常执行 `docker compose restart` 或 `docker compose up -d` 不会清空数据；但执行 `docker compose down -v` 会删除 volume，需要谨慎。

主要业务表包括：

| 服务 | 表 | 内容 |
| --- | --- | --- |
| identity-service | `users`, `sessions` | 用户与登录会话 |
| consultation-service | `encounter_sessions` | 一次完整接诊 |
| consultation-service | `consultation_sessions` | 问诊流程状态 |
| consultation-service | `consultation_turns` | 每一轮问答 |
| assessment-service | `assessment_sessions` | 量表测评会话 |
| assessment-service | `assessment_answers` | 量表题目答案 |
| assessment-service | `assessment_results` | 量表结果 |
| multimodal-service | `multimodal_sessions` | 多模态会话 |
| multimodal-service | `multimodal_audio_turns` | 音频轮次、ASR 结果 |
| multimodal-service | `multimodal_captures` | 多模态采集记录 |
| multimodal-service | `multimodal_inference_results` | 多模态推理结果 |
| multimodal-service | `multimodal_turn_bundles` | turn 级聚合结果 |
| risk-service | `risk_evaluations`, `risk_triggers` | 风险评估与触发记录 |
| intervention-service | `intervention_sessions`, `intervention_events` | 干预会话与事件 |

进入数据库排查：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.lan-https.yml \
  exec postgres psql -U mcs -d mcs
```

常用查询：

```sql
\dt

select id, user_id, status, created_at
from consultation_sessions
order by created_at desc
limit 10;

select id, session_id, question_text, transcript_text, created_at
from consultation_turns
order by created_at desc
limit 20;

select id, session_id, transcript_text, audio_uri, processing_status, created_at
from multimodal_audio_turns
order by created_at desc
limit 20;
```

### 大对象存储

音频原始文件、标准化 wav、部分采集对象等大文件走 MinIO。Compose 中默认配置：

```text
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

常见 bucket：

```text
mcs-multimodal
mcs-consultation
```

数据库通常只保存对象引用，例如：

```text
audio_uri
normalized_wav_uri
storage_provider
storage_object_key
storage_uri
```

因此排查音频或采集文件时，通常需要同时看 PostgreSQL 记录和 MinIO 对象。

### 实时热状态

Redis 用于保存实时状态，不是长期业务数据的唯一来源。典型用途：

- EEG 当前状态
- 视觉采集当前状态
- live stream 状态
- turn 级临时聚合状态

典型 key 形态：

```text
eeg:live:{session_id}
eeg:turn:{session_id}:{turn_id}:state
visual:live:{session_id}
visual:turn:{session_id}:{turn_id}:aggregate
live:stream:{session_id}
```

Redis 数据通常带 TTL。如果 Redis 重启，未最终落库的热状态可能丢失；历史记录应以 PostgreSQL 中的会话、turn、结果表为准。

### 前端本地存储

浏览器 `localStorage` / `sessionStorage` 只保存登录 token、会话恢复信息等前端状态，例如当前 consultation / assessment session id。它不是正式业务数据源。

### API 查询入口

前端通常通过 gateway 查询：

```text
GET /api/v1/consultations/{session_id}
GET /api/v1/consultations/{session_id}/multimodal/live
GET /api/v1/consultations/{session_id}/turns/{turn_id}/multimodal/bundle
GET /api/v1/assessment/sessions/{session_id}
GET /api/v1/assessment/sessions/{session_id}/multimodal/live
```

简要结论：

```text
YAML/静态目录定义交互内容；
PostgreSQL 记录真实交互历史；
MinIO 存音频、采集文件等大对象；
Redis 存实时热状态；
浏览器 localStorage/sessionStorage 只做前端会话恢复。
```

## 11. 隐藏本地 LFS / 部署产物改动

补齐真实模型和视频后，`git status` 会显示大量资源文件变为 `modified` 或 `untracked`。这些资源是本地部署所需，但不应作为普通 Git 文件提交。

### tracked 的 LFS 资源：使用 skip-worktree

对已经被 Git 追踪、但本地被真实大文件替换的 LFS 资源，使用 `skip-worktree` 隐藏：

```bash
git -C /home/medai/depression-system ls-files -z \
  apps/consultation/client/public/digital-human \
  apps/consultation/client/public/intervention/audio \
  apps/consultation/client/public/intervention/video \
  services/multimodal-service/runtime-assets \
  | grep -zE '\.(webm|onnx|pt|mp3|mp4)$' \
  | xargs -0 git -C /home/medai/depression-system update-index --skip-worktree

git -C /home/medai/depression-system-zhurui-sync ls-files -z \
  apps/consultation/client/public/digital-human \
  apps/consultation/client/public/intervention/audio \
  apps/consultation/client/public/intervention/video \
  services/multimodal-service/runtime-assets \
  | grep -zE '\.(webm|onnx|pt|mp3|mp4)$' \
  | xargs -0 git -C /home/medai/depression-system-zhurui-sync update-index --skip-worktree
```

查看隐藏数量：

```bash
git -C /home/medai/depression-system ls-files -v \
  | awk '$1 ~ /^S/ {c++} END {print c+0}'

git -C /home/medai/depression-system-zhurui-sync ls-files -v \
  | awk '$1 ~ /^S/ {c++} END {print c+0}'
```

如需恢复显示：

```bash
git -C /home/medai/depression-system ls-files -v \
  | awk '$1 ~ /^S/ {print substr($0, 3)}' \
  | grep -E '\.(webm|onnx|pt|mp3|mp4)$' \
  | xargs -r git -C /home/medai/depression-system update-index --no-skip-worktree
```

### untracked 的本地部署产物：使用 `.git/info/exclude`

两个 worktree 共用主仓库的本地 exclude：

```text
/home/medai/depression-system/.git/info/exclude
```

本次加入了以下本地规则：

```gitignore
# Local deployment/runtime assets restored from Git LFS pointers.
# Keep these files available for local Docker builds, but do not show them as
# ordinary untracked files in either worktree.
apps/consultation/client/public/digital-human/**/*.webm
apps/consultation/client/public/intervention/audio/*.mp3
apps/consultation/client/public/intervention/video/*.mp4
services/multimodal-service/runtime-assets/models/**/*.plan
```

注意：`.git/info/exclude` 是本地配置，不会提交到仓库，适合隐藏本机部署产物。不要把真实 `.onnx`、`.pt`、`.webm`、`.plan` 作为普通 Git 文件提交。

### index.lock 残留

如果执行 `git update-index` 时遇到：

```text
Unable to create '.git/index.lock': File exists.
```

先确认没有 git 进程：

```bash
ps -ef | grep -E '[g]it'
```

如果没有进程且锁文件是残留空文件，可以删除：

```bash
rm /home/medai/depression-system/.git/index.lock
```

然后重新执行 `git update-index --skip-worktree`。

本次整理后：

```text
主 worktree 只剩代码/配置改动:
  infra/compose/docker-compose.gpu.yml
  services/multimodal-service/Dockerfile
  services/multimodal-service/app/services/non_eeg_runtime.py
  services/multimodal-service/requirements-heavy.txt

zr worktree 只剩文档/代码改动:
  README.md
  services/multimodal-service/Dockerfile
  docs/operations/jetson-gpu-https-deployment-troubleshooting_20260727.md
```

## 12. 提交注意事项

本次为本地运行补齐了大量 LFS 大文件，因此 `git status` 会看到很多资源文件变为 `modified` 或 `untracked`，包括：

- `apps/consultation/client/public/digital-human/**/*.webm`
- `services/multimodal-service/runtime-assets/**/*.onnx`
- `services/multimodal-service/runtime-assets/**/*.pt`
- `services/multimodal-service/runtime-assets/**/*.plan`

不要把这些大文件作为普通 Git 文件直接提交。

建议只提交文本改动，例如：

- `README.md`
- `docs/operations/jetson-gpu-https-deployment-troubleshooting_20260727.md`
- `services/multimodal-service/Dockerfile`

大资源文件应通过 Git LFS 或部署制品管理。
