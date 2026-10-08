# Jetson 项目移植与部署检查（2026-10-07）

检查结论：当前 Jetson Orin Nano 上的主业务链已成功运行，未发现正在发生的整体启动或 GPU 推理故障；但存在需要修复的前端错误、HTTPS 会话配置问题、容量风险和部署可复现性问题。不能据此认定整个项目已完成生产部署验收。

本次检查没有修改业务代码或线上部署配置，没有重启服务，也没有清理已有 Docker 镜像、缓存或业务卷。验收创建了标记为“非真实患者”的测试账号和记录；真实患者数据未用于测试。

## 已实际验证

| 检查项目 | 结果与范围 |
| --- | --- |
| 当前 Compose 配置、基础 Compose 配置、Caddy 配置 | 验证通过；当前 Compose 为 v2.32.4 |
| 容器运行状态 | 14 个容器运行，已有 Docker 健康检查的容器均 healthy；检查时 RestartCount 为 0，无 OOMKilled |
| 应用就绪接口 | 10 个应用 `/health/ready` 均返回 200，MinIO 就绪接口返回 200；这不代表健康接口已检查所有依赖 |
| 数据库迁移 | identity、consultation、assessment、risk、intervention、followup、multimodal 的 Alembic current 均为 head |
| 运行代码一致性 | 8 个领域/网关服务和 2 个前端服务的 Python app 源码与工作区一致 |
| 资源完整性 | 96 个 Git LFS 文件均存在，未发现未展开的 LFS pointer；当前 Compose 的 bind 源路径均存在 |
| HTTPS | 使用 `jetson-local-ca.pem` 验证证书后，两套前端可访问；证书覆盖当前 IP `192.168.50.41` 和 localhost |
| 浏览器 | Chromium 问诊登录、后台登录和页面渲染通过，pageerror 为空 |
| 基础问诊和音频 | 注册、资料保存、问诊启动、会话关联、五模态预热、4 秒预录音频上传、转写、情绪分析及对象存储链路通过 |
| 业务链 | 使用合成账号完成问诊至 handoff_ready、PHQ-9 九题作答、风险评估创建及查询、干预会话和完成事件保存、历史详情与 PDF 下载；PDF 为 11848 字节 |
| GPU | CUDA 张量运算通过；文本、人脸、姿态、语音的四个板端 TensorRT 引擎使用合成模型输入实际执行，输出均为有限数值 |
| CPU 回退 | 0.5 秒合成音频超出 TensorRT profile 后成功回退 ONNX CPU，输出为有限数值 |
| 已有回归测试 | consultation 23、multimodal 30、eeg-tools 31、前端 EEG 10，共 94 项通过 |
| 前端打包 | 在临时副本用锁文件安装依赖后，Vite 构建通过 |
| 前端类型检查 | **失败：2 处 TypeScript 错误**，详见下文 |
| 仓库常规检查 | `make compose-config`、`make phase-check`、新增部署脚本语法检查通过；phase-check 的通过不包含 TypeScript 或业务测试 |

容器原本没有 pytest，前端宿主机没有 node_modules。本次使用临时依赖目录运行测试；consultation 测试按仓库目录布局放入临时目录，以满足现有测试的路径假设。测试依赖未覆盖容器应用依赖。

## 需要优先处理的问题

### 1. 磁盘容量不足且容器日志没有轮转（高）

检查开始时根分区已使用 98%，可用约 4.3 GB。`docker system df` 显示构建缓存约 11.33 GB；不能将该数字和可回收镜像大小直接相加，因为可能存在共享层。

所有当前容器使用 `json-file`，LogConfig.Config 为空，没有 max-size/max-file。服务健康探测会持续产生访问日志，录音和视频也会继续占用磁盘。磁盘写满会影响 PostgreSQL、对象存储、容器日志及下次镜像构建。

建议先明确保留策略后释放不用的构建缓存，再配置日志轮转并监控剩余容量。不要删除业务卷、运行中的镜像或 `.codex-tmp/tensorrt` 引擎。本次没有执行 Docker prune。

### 2. 特定视频节点缺少 URL 时，前端会抛异常（高）

位置：[consultationVideoNode.ts](../../apps/consultation/client/src/features/video-node/consultationVideoNode.ts#L15)。

`normalizeVideoNodeUri()` 允许返回 null，但 `resolveConsultationVideoUri()` 在 videoAssetId 为 `risk-screening-review-002` 时直接执行 `videoUri.split()`。用该节点 ID 和 null 视频地址调用实际导出函数，已复现：

```text
TypeError: Cannot read properties of null (reading 'split')
```

这属于输入缺失情况下的真实运行错误；正常配置中视频地址完整时，本次常规浏览器验收没有触发它。建议先检查 videoUri 是否存在，再处理版本参数。

另一个类型错误位于 [SummaryDashboard.tsx](../../apps/consultation/client/src/features/result-page/components/SummaryDashboard.tsx#L169)：`getModuleScoreTooltip()` 的结果可能为 null，却传给要求 `readonly string[]` 的 content。应缓存返回值，再通过条件判断收窄类型。此处本次只确认了类型检查错误，未观察到运行异常。

### 3. HTTPS 登录 Cookie 缺少 Secure，HTTP 页面仍对外开放（高）

位置：[gateway auth.py](../../services/gateway-service/app/api/auth.py#L32)、[Jetson Compose](../../infra/compose/docker-compose.jetson-nano.yml#L105)。

实际 HTTPS 登录响应的 Cookie 属性为 `HttpOnly; Path=/; SameSite=lax`，没有 Secure。同一主机的 80、3000、3001 HTTP 端口仍开放，因此浏览器访问相同主机的 HTTP 地址时可能携带登录 Cookie；80 端口的 HTTPS 重定向不能保护首次 HTTP 请求中的 Cookie。

建议在 Jetson HTTPS 配置中启用 Secure Cookie，并将 3000/3001 限制到本机，统一通过 443/8443 使用系统。已验证默认演示管理员密码仍可登录；真实数据使用前应替换演示凭据。

## 部署和移植隐患

### 4. 对外开放的 HTTP 前端不能正常连接网关（中）

两套 HTTP 前端配置都将 API 指向 `http://<板子IP>:18080/api/v1`。但 Jetson Compose 把网关只绑定在 `127.0.0.1:18080`。

实测 `http://192.168.50.41:3000/config.js` 和 3001 的配置可读取，而 `http://192.168.50.41:18080/health/live` 连接被拒绝。故局域网用户通过 3000/3001 能打开页面，但登录/API 请求失败。HTTPS 443/8443 的同源代理已通过验收。

建议收紧 HTTP 前端端口，并在部署文档中固定 HTTPS 入口。

### 5. 宿主机包整体挂载导致依赖混用（中）

位置：[Jetson Compose](../../infra/compose/docker-compose.jetson-nano.yml#L69)、[host runtime requirements](../../services/multimodal-service/requirements-jetson-host-runtime.txt#L29)。

当前挂载整套宿主机 Python 包和库。`pip check` 未通过，其中直接涉及当前运行包的冲突包括：

- torch 要求 `sympy==1.13.1`，实际为 1.14.0。
- httpcore 1.0.7 要求 `h11<0.15`，实际为 0.16.0。

此外存在宿主机 TensorFlow、Keras 等其他包的冲突及缺少依赖。不能把这些全都视为本项目当前功能已经失败；本次 CUDA、TensorRT、MediaPipe 导入及音频业务链实际通过。但这说明运行环境未形成一致的依赖集合，宿主机升级可能影响容器。

建议先针对实际使用的包建立经过验证的约束，缩小宿主机依赖挂载范围，不要为了让整个宿主机包集合的 pip check 通过而随意升级 GPU 包。当前 PyTorch 为 `2.5.0a0+872d972e41.nv24.08`，CUDA 12.6，TensorRT 10.7，MediaPipe 0.10.18。

### 6. Redis 使用匿名卷，持久化策略不足（中）

位置：[基础 Compose](../../infra/compose/docker-compose.dev.yml#L16)、[Jetson override](../../infra/compose/docker-compose.jetson-nano.yml#L14)。

实际 Redis `/data` 挂载的是匿名卷；配置为 RDB 默认 save 策略、`appendonly=no`、`maxmemory=0`。执行 down 后再 up，不会自动把原匿名卷作为新服务的数据源。正常运行中的容器重启与 down/up 的影响不同。

风险主要涉及多模态临时聚合、EEG transport stream 及消费状态，不应误解为 PostgreSQL 中的正式业务记录会随 Redis 丢失。宿主机 `vm.overcommit_memory=0`，Redis 启动日志也已提示低内存时后台保存可能失败。

建议明确哪些 Redis 数据允许丢失；需要延续的数据使用命名卷和相应持久化策略，同时设置内存预算。RDB 最近一次保存状态为 ok，未发现当前保存故障。

### 7. 健康检查尚不能证明业务依赖就绪（中）

[assessment](../../services/assessment-service/app/main.py#L18)、[risk](../../services/risk-service/app/main.py#L20)、[intervention](../../services/intervention-service/app/main.py#L20) 的 ready 直接返回 ready；[multimodal](../../services/multimodal-service/app/main.py#L59) 主要判断 EEG 状态，没有完整验证数据库、对象存储和四模态/ASR 可用性。

这是代码审查确认的覆盖不足，本次没有通过停数据库或停 MinIO 对线上服务实施故障注入。依赖出问题时，有可能出现 healthy 但业务请求失败。`restart: unless-stopped` 也不会仅因为 unhealthy 自动重启容器。

建议分别设计轻量依赖就绪检查和独立的模型验收探测，避免每次 healthcheck 都重新加载模型。

### 8. 新机器部署及重建还不够可复现（中）

- Jetson Compose、Dockerfile、运行脚本等关键部署文件在检查时仍是 untracked；只克隆当前提交不会得到这些文件。
- 四个必需引擎位于忽略目录 `.codex-tmp/tensorrt`。当前文件齐全，但清理该目录会导致容器无法重新创建；新机器必须先满足宿主机依赖要求并构建本机引擎。
- [consultation Dockerfile](../../apps/consultation/Dockerfile#L9) 没有复制 package-lock.json，使用 npm install；这会使 Docker 重建不按仓库锁文件固定依赖。建议改为复制锁文件并使用 npm ci。
- Docker 的前端构建只运行 Vite，没有执行 typecheck，因此本次两处 TypeScript 错误被放过。
- [multimodal pyproject](../../services/multimodal-service/pyproject.toml#L5) 声明 Python >=3.11，Jetson 实际运行 Python 3.10。当前 Docker 不按该元数据安装项目，所以已经跑通，但原生安装/打包要求不一致。
- [README 的快速检查](../../README.md#L65) 使用 8080 和 8000，当前网关宿主机端口是 18080，前端是 3000；8080 实测连接被拒绝。默认 operations-console config.js 也仍指向 8080，Jetson 专用 override 已修正 HTTPS 入口。
- 当前部署固定用了 `http://127.0.0.1:17897` 构建代理以及本机 CUDA/用户目录；迁移到其他机器时需要重新核对，不能直接假定这些路径和代理存在。

建议在整理并提交部署文件后，记录宿主机 GPU 依赖版本、资产校验和、引擎重建步骤及证书生成步骤。管理当前这套部署时使用 `scripts/jetson-stack.sh`，保持 Compose 文件组合和项目名一致。

## 功能边界和未验证项目

- [followup-service](../../services/followup-service/app/main.py) 当前只注册健康接口，没有随访业务路由，网关也没有对应路由；它运行正常不代表随访业务闭环已经实现。这是现有功能边界，不是本次移植造成的故障。
- 尚未验证实体摄像头、麦克风、BLE EEG 真机、完整视频驱动浏览器问诊和多用户并发。GPU 引擎的合成输入验证不等于真实摄像头识别验收。
- 本次业务链完整作答验证的是 PHQ-9 示例路径，未穷举所有量表、风险分支和干预内容。
- 内存初始可用约 1.1 GiB，检查后可用约 1.6 GiB；已有约 4.1 GiB swap 使用。单会话验收通过，不能推断并发容量。
- PostgreSQL、MinIO 和报告目录使用命名卷，但仓库未见配套备份/恢复流程；本次没有执行恢复演练，也未验证宿主机外部备份任务。
- Docker 已启用开机启动、容器有 restart 策略；没有重启整机测试开机恢复。

本次通过的完整业务链测试账号为 `jetson-full-audit-236777e8@mcs.local`，encounter 为 `b286a608-9b6b-4509-92a0-ac3f91c7c08b`。基础音频验收账号为 `jetson-deployment-smoke-4bf46566@mcs.local`。另有两个合成账号来自验收脚本调试；测试记录未自动删除。

修复顺序建议：先解决视频空值错误和 HTTPS Cookie，再处理磁盘/日志及 HTTP 端口，随后收敛依赖、Redis 持久化、健康检查与部署可复现性。
