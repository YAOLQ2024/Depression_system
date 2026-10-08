# Jetson 磁盘与局域网部署优化方案（2026-10-07）

这是检查结果与建议实施方案。本轮没有删除文件、调整分区、修改服务配置或重启服务。

## 磁盘的实际情况

- SSD 物理容量 256.06 GB，即 238.47 GiB。
- 根分区 `/dev/nvme0n1p1` 大小 174.92 GiB；ext4 的文件系统统计总量为 171.12 GiB（df -h 显示约 172G）。
- 检查时文件系统已用 159.60 GiB，普通用户可用 4.25 GiB（约 4.3G），另有约 7.26 GiB 空闲但普通用户不可使用的空间。不要直接把这部分都当成可用容量。
- 从 sysfs 中 SSD 扇区总数、各分区起始位置和长度计算，最后一个已分配分区之后仍有约 62.10 GiB 未分配。根分区是磁盘上物理位置最后的分区，具备向后扩展的空间；实施前仍须核对 GPT 分区表。
- 原部署文档记录部署前剩余约 16 GB。这是既有记录，不是本次重新测量的历史值；没有完整的部署前磁盘快照，不能精确将所有新增占用归因到某个构建步骤。

## 已定位的空间占用

目录数据为 du 显示的量级，Docker 项为 Docker 显示的量级，两种工具的单位不同；各项目也可能有包含关系或共享层，不能直接相加。

| 来源 | 大小 | 处理建议 |
| --- | --- | --- |
| `/usr/share/ollama` | 约 37G | 先核对现有模型及其他程序依赖，按模型管理方式移除不用的内容，不直接删除整个目录 |
| `/home/jetson/workspaces/isaac_ros-dev` | 约 16G | 属于既有 ROS 工作区，保留需要的代码和数据，按项目需要清理可重新生成的构建输出 |
| Docker 构建缓存 | 11.33 GB | 可先清理较旧、未使用的构建缓存；代价是之后重建更慢 |
| 未被容器使用的 open-webui、ROS、label-studio 镜像 | 合计约 9.03 GB | 分别约 3.72、4.65、0.66 GB；是否删除需考虑其他项目和离线重建需求 |
| `/var/log/uvcdynctrl-udev.log` | 约 6.5G | 单文件约 6.95 GB，最后修改于 2026-05-29；先确认保留需求，再归档或清空，补日志轮转及产生原因检查 |
| `/home/jetson/.cache` | 约 8.2G | Hugging Face 约 5.4G、uv 约 2.1G、pip 约 379M；模型缓存需先确认其他程序依赖 |
| 本项目目录 | 约 6.8G | `.git` 约 3.5G、runtime-assets 约 1.7G、前端 public 约 1.3G；模型/视频本体及 Git LFS 对象有重复存储，部署镜像和构建层还会产生副本 |

本项目 PostgreSQL 卷约 50.9 MB，MinIO 卷不到 1 MB；当前新增业务数据不是主要的磁盘占用来源。

## 推荐的磁盘处理顺序

1. 先盘点并清理可以重新生成的旧构建缓存，再处理异常大日志。
2. 为容器设置日志轮转，例如每个容器 `max-size: 10m`、`max-file: 3`；为系统大日志补轮转。当前占用较大的 uvcdynctrl 日志属于宿主机日志，Docker 日志轮转不会处理它。
3. 备份业务数据库、对象存储及分区表后，利用 SSD 上未分配的约 62 GiB 扩展根分区，再扩展 ext4 文件系统。这比长期依赖删缓存更稳定。
4. 建立磁盘容量告警及缓存保留预算；部署构建留出足够空间，避免边录音边进行大镜像构建。

可用于优先清理旧构建缓存的命令是：

```bash
docker builder prune --filter 'until=168h'
df -h /
```

实际释放量以 prune 返回结果和 df 为准；该命令不能保证释放全部 11.33 GB。不同 Docker/buildx 版本的 `-a` 含义应以本机 help 为准，不使用通用的 `docker system prune --volumes` 清理业务系统。

根分区扩展操作的典型工具是 growpart 和 resize2fs。growpart 本机尚未安装，调整分区需要管理员权限；本轮没有执行。本机是 Jetson 的多分区启动布局，只扩展确认有后方空闲的 p1，不调整其他启动分区。

参考：[Ubuntu growpart 手册](https://manpages.ubuntu.com/manpages/jammy/man1/growpart.1.html)、[Ubuntu resize2fs 手册](https://manpages.ubuntu.com/manpages/jammy/man8/resize2fs.8.html)。

## 局域网的目标访问方式

- 问诊系统：`https://192.168.50.41`
- 管理后台：`https://192.168.50.41:8443`
- 页面、登录 API、上传、视频资源和 SSE 通过相应 HTTPS 入口访问；内部 PostgreSQL、Redis、MinIO 和领域服务继续通过 Docker 内部网络访问。
- 给 Jetson 配置 DHCP 地址保留，或部署稳定域名，避免 IP 改变后客户端书签和证书失效。
- 放行局域网访问入口端口，检查 Wi-Fi 访客网络/AP isolation 是否阻止客户端间访问。
- 将旧 HTTP 页面入口重定向到正式 HTTPS 入口，避免用户进入可打开页面但不能完成 API/媒体采集的旧地址。

这满足“局域网设备使用整个系统”的目标：用户通过统一网址访问所有业务能力，无需将数据库或每个微服务端口都公开到局域网。

## 摄像头、麦克风正常使用的条件

浏览器的 getUserMedia 需要安全上下文和用户授权。局域网 HTTP IP 地址不满足通常的安全上下文要求；详情见 [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)。

当前证书覆盖 IP 且用指定 CA 可验证，但系统默认 curl 验证返回 `unable to get local issuer certificate`。因此“服务有 HTTPS”与“客户端已信任证书”是两项检查。

可选择以下方案：

1. 保留当前本地 CA：在每台客户端安装并信任 `infra/certs/jetson-local-ca.pem`。只分发 CA 公钥证书，不分发私钥。还要在客户端操作系统和浏览器中允许摄像头/麦克风。
2. 若希望更多设备无需安装本地 CA：使用自己控制的域名和公认 CA 签发的证书，将域名在局域网内解析到 Jetson。DNS 验证可用于没有公网入站端口的部署；需要对应域名/DNS 配置。

录音代码已经使用 MediaRecorder.isTypeSupported 动态选择 OGG/WebM/MP4，后端也接受这些格式并做转码。仍须在 Windows/Android/iOS 的目标浏览器中验证真实设备、视频播放和实际上传处理。

本轮 Chromium 虚拟设备检查在 `https://192.168.50.41` 上成功取得 live audio/video tracks，isSecureContext 为 true。该测试忽略了证书错误并使用虚拟设备，因此仅证明媒体 API 没有被页面/服务阻断，不能代替真实客户端证书信任及硬件验收。

客户端采集的是客户端本机的摄像头和麦克风。现有 BLE EEG bridge 运行在 Jetson 上；若 EEG 设备位于远端客户端，需要另外设计该客户端到服务的 EEG transport，并不能只靠浏览器摄像头权限实现。

## 上轮各项问题的优化方式

| 问题 | 优化方式 | 验收要求 |
| --- | --- | --- |
| 磁盘/日志 | 旧缓存盘点、异常日志处理、日志轮转、扩展 p1、容量监控 | df 容量达到预算，连续采集时日志及临时目录有界 |
| 前端两处错误 | videoUri 空值保护；缓存并收窄 tooltip 返回值 | 原先 null.split 复现不再报错，npm run typecheck 和 Vite build 均通过 |
| HTTPS 会话 | 增加 SESSION_COOKIE_SECURE 配置，Jetson HTTPS 环境启用，开发 HTTP 环境保持相应设置；退出 Cookie 属性与登录一致 | HTTPS 登录响应有 Secure/HttpOnly/SameSite，退出失效，现有登录链不回归 |
| LAN HTTP/API 入口 | 使用稳定 HTTPS 入口和同源 API，旧入口重定向或明确收敛 | 从另一台客户端登录、上传、获取 SSE、播放视频全部通过，无错误的 localhost/API 端口 |
| 宿主机依赖混用 | 先固定实际使用包的兼容版本，包括 SymPy、httpcore、h11；逐步改为经过验证的专用 GPU 依赖目录或可复现镜像 | 项目实际依赖一致、GPU 推理和 ASR 通过；不靠任意升级宿主机 GPU 包解决冲突 |
| Redis | 先备份/迁移当前匿名卷数据，再改命名卷；根据需要启用 AOF everysec，设内存预算和明确淘汰规则；评估 vm.overcommit_memory | 容器重建后所需 stream/消费状态保留；避免误删业务卷，不随意驱逐采集 stream |
| readiness | 验证数据库连通性/必要表、Redis、对象存储，模型状态使用缓存的初始化/验收结果；不在每次健康检查加载大模型 | 在隔离测试环境模拟依赖故障返回 503；live 与 ready 语义区分 |
| 可复现部署 | Docker 使用 package-lock + npm ci 并执行 typecheck；统一 Python 要求；引擎移出临时目录并记录模型/版本/校验和；整理并提交部署配置 | 在另一台匹配 JetPack 的机器按文档可重建；缺资源有明确预检报错 |
| 数据备份 | 对 PostgreSQL、MinIO、报告、配置建立备份及保留策略，在隔离环境演练恢复 | 能恢复记录与其关联媒体，备份容量纳入磁盘预算 |
| 并发与性能 | 限制推理并发、排队和超时；监测 CUDA/CPU 回退、内存和 swap；逐步测试真实会话 | 用实际测量确定可承载人数；多个客户端能访问不代表可以不限并发 |
| followup 功能边界 | 按随访业务设计实现接口、模型与网关/前端流程 | 业务闭环测试通过；仅部署容器不能补齐尚未实现的功能 |

推荐先完成容量处理、HTTPS/证书/局域网真实设备验收与前端错误修复，再收敛依赖、Redis、健康检查、备份及可复现构建。新增随访业务需要单独明确功能范围。
