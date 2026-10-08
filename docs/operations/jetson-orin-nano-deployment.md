# Jetson Orin Nano 8 GB 部署

本配置面向 Ubuntu 22.04 / JetPack 6.x、Python 3.10 的板端，适用于已安装并验证 NVIDIA PyTorch、torchaudio、MediaPipe 和 TensorRT 的机器。它叠加基础 Compose 与 LAN HTTPS 配置，保持所有业务服务在容器内，其他服务仍通过 `multimodal-service:8000` 访问多模态服务。

## 资源与兼容性

原 GPU 配置使用 NVIDIA PyTorch 25.06 完整镜像。本机只有约 16 GB 剩余磁盘，采用单独的 `Dockerfile.jetson-host-runtime`，只读挂载宿主机已有的 Python GPU 包和 JetPack 库，避免复制 PyTorch 和 CUDA。镜像内应用依赖优先，宿主机包只作为补充。不要升级或删除这些宿主机依赖后直接继续使用原容器，先重新执行 GPU 验证。

服务仍使用 PostgreSQL、Alembic 迁移、Redis 和 MinIO。模型与视频须先通过 Git LFS 完整检出。TensorRT `.plan` 必须与当前板子、TensorRT 和模型匹配；不匹配时应重新生成或关闭 `MCS_TENSORRT_ENABLED`，不能直接复用其他板子的引擎。

本机 EEG transport 采用 Redis Stream，但就绪检查不要求真实 EEG 设备已连接。没有设备时 EEG 不产生有效采集结果，也不自动注入模拟数据。需要真机时再叠加仓库的 `docker-compose.jetson-eeg-bridge.yml`。

## 启停

新板先启动 CPU 模式并完成四模态端到端验证，再构建本板引擎：

```bash
MCS_TENSORRT_ENABLED=false ./scripts/jetson-stack.sh up -d --build
python3 scripts/jetson-build-engines.py
python3 scripts/jetson-verify-engines.py
```

升级后的引擎写入 `.codex-tmp/tensorrt-upgrade-20261007/`，独立只读挂载到 `/app/board-engines`；旧本板引擎保留在 `.codex-tmp/tensorrt/` 供回退。GPU profile 支持文本长度 2–256、姿态 8–96 帧、RGB 224×224 人脸和 0.5–10 秒语音情绪分析；超出 profile 的有效输入使用原始 ONNX CPU 推理。新姿态模型在 FP16 的 96 帧输入上出现 NaN，因此构建脚本对姿态使用 FP32，其余采用混合 FP16。ASR 始终使用本机 CUDA PyTorch。

基础 Jetson Compose 默认 CPU，不要求引擎目录存在。完成 CPU/GPU 输出验证后，创建 `.codex-tmp/tensorrt.enabled` 标记启用独立 TensorRT 覆盖配置。启动、重启与临时运行前检查 ONNX、plan 哈希及 L4T 版本；不匹配时拒绝启用，需重建或显式切回 CPU。GPU 运行期间不要删除当前引擎目录。移植其他板不复制引擎和启用标记。

```bash
touch .codex-tmp/tensorrt.enabled # 仅在本板模型与引擎输出验证通过后执行
./scripts/jetson-stack.sh up -d --build
./scripts/jetson-stack.sh ps
./scripts/jetson-stack.sh logs --tail=100 multimodal-service
./scripts/jetson-stack.sh stop
./scripts/jetson-stack.sh start
```

所有服务配置 `restart: unless-stopped`。PostgreSQL、MinIO 和导出报告使用持久卷；不要使用 `down -v` 删除业务数据。

## HTTPS

证书位于 `infra/certs/`，私钥不提交 Git。证书需覆盖 localhost 和板子当前局域网 IP。其他设备访问前，应信任本机 CA 文件 `infra/certs/jetson-local-ca.pem`；只传 CA 证书，不传任何 `*-key.pem`。

- 问诊前端：`https://<板子IP>`
- 管理后台：`https://<板子IP>:8443`

两套前端的 API 均通过当前 HTTPS 地址访问网关。IP 改变后重新签发服务器证书，并重启 Caddy。

2026-10-07 局域网修复后，HTTP 3000/3001 由 Caddy 接管，分别跳转至 HTTPS 443/8443；前端容器不再直接发布 HTTP 端口。本机系统与 Chromium 已导入 CA 信任。其他设备的证书安装及媒体授权步骤见 [局域网客户端访问说明](lan-client-access.md)。

## 网络与构建

MinIO 的 Docker Hub / Quay 社区镜像以及历史二进制地址在本次部署时均不可访问。本配置按照[官方源码构建说明](https://github.com/minio/minio)，固定 `RELEASE.2025-10-15T17-29-55Z`，通过 `infra/minio/Dockerfile` 构建本地 ARM64 镜像，避免依赖已撤下的 `minio/minio:latest`。

构建使用 host 网络，通过 `MCS_BUILD_PROXY` 指定本机 HTTP 代理，默认 `http://127.0.0.1:17897`。应用运行时不配置外网代理。若 Docker daemon 无法联网，可用 regctl 将官方 ARM64 镜像导出后通过 `docker load` 导入，无需修改全局 daemon 配置。

## 验收

启动后检查 Compose 状态、所有服务的 `/health/ready`、HTTPS 前端、数字人视频、登录、问诊会话和多模态 warmup。GPU 验证需包括 CUDA 张量计算、ASR 模型加载和实际推理。真机摄像头、麦克风及 EEG 采集还需在具备对应设备的浏览器中完成。

基础验收脚本会创建标记为“非真实患者”的独立测试账号和问诊记录，不修改默认演示账号的资料：

```bash
python3 scripts/jetson-smoke.py
```

语音链路验收使用仓库内的数字人问候视频作为预录测试素材：

```bash
docker exec -i mcs-jetson-multimodal-service-1 ffmpeg \
  -y -hide_banner -loglevel error -i pipe:0 -t 4 -vn -ac 1 -ar 16000 \
  /tmp/mcs-smoke-greeting.wav \
  < apps/consultation/client/public/digital-human/consultation-v1/greeting-001.webm
docker cp mcs-jetson-multimodal-service-1:/tmp/mcs-smoke-greeting.wav /tmp/mcs-smoke-greeting.wav
python3 scripts/jetson-smoke.py --audio-fixture /tmp/mcs-smoke-greeting.wav
```

## 本机部署结果（2026-10-07）

- 硬件：Jetson Orin Nano Super 开发套件，8 GB；Ubuntu 22.04.5，L4T R36.4.3，CUDA 12.6，TensorRT 10.7。
- 项目目录：`/home/jetson/Documents/depression-system`，分支 `feature/zhurui`。
- 问诊前端：[https://192.168.50.41](https://192.168.50.41)，板子本机也可用 [https://localhost](https://localhost)。演示账号 `participant@mcs.local`，密码 `Participant123!`。
- 管理后台：[https://192.168.50.41:8443](https://192.168.50.41:8443)。演示账号 `admin@mcs.local`，密码 `Admin123!`。
- Docker 已启用开机启动；14 个容器正在运行，配置 `restart: unless-stopped`。用户主动执行 `stop` 后需执行 `start` 恢复。

| 验收项目 | 结果 |
| --- | --- |
| 10 个应用服务 readiness、PostgreSQL、Redis、MinIO | 通过 |
| CA 验证的 HTTPS、两套前端、数字人 WebM | 通过 |
| Chromium 问诊登录、管理后台登录及页面渲染 | 通过，浏览器无脚本异常 |
| 注册、资料、问诊启动、会话关联、五模态预热 | 通过 |
| CUDA 张量计算；文本、人脸、姿态 GPU 推理 | 通过，输出为有限数值 |
| 4 秒预录音频上传、MinIO 原音频和 WAV 存储、CUDA Dolphin 转写、语音及文本情绪分析 | 通过，处理状态 `completed` |
| TensorRT 不兼容引擎回退、0.5 秒音频超出 profile 的 CPU 推理 | 通过 |
| Compose 配置、Python 编译、`make phase-check` | 通过；宿主机未安装 FastAPI 的提示不影响容器内服务 |
| 实际摄像头、麦克风、EEG 采集 | 未验证，需要连接设备后联调 |

首次部署验收时约 1.1 GB 内存可用、10 GB swap 可用，磁盘剩余约 4.4 GB。后续已清理旧日志并修复局域网访问，见 [2026-10-07 修复验收](jetson-lan-fix-20261007.md)。该验收覆盖单会话功能链路，没有进行并发压力测试。启动更多服务或重新构建大型镜像前应先检查容量。

所有证书私钥与引擎产物已排除 Git；源码和部署配置改动保留在工作区，未自动提交或推送。

四模态新模型、姿态精度修复、标签兼容和 30 分钟并发验收见 [四模态升级报告](jetson-four-modal-upgrade-20261007.md)。上表为升级前的首次部署记录，新模型的状态与性能以升级报告为准。
