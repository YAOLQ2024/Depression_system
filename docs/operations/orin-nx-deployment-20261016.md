# Orin NX 部署与资源验收（2026-10-16）

当前部署已启动，14 个项目容器运行；有健康检查的容器均 healthy，检查时无异常重启、无 OOM。项目分支 feature/zhurui，提交 90f84a17b6c4d6ebd5d7534ced1c6efb27367b37（2026-10-11）。改动保留在本机，未提交或推送。

## 访问与操作

- 问诊：https://localhost/ 或 https://192.168.50.11/
- 管理后台：https://localhost:8443/ 或 https://192.168.50.11:8443/
- 本机应用菜单新增“MCS 问诊系统”，调用 scripts/open-orin-nx-browser.sh，使用经验证的 NVIDIA GPU 图形路径。
- 演示受试者：participant@mcs.local / Participant123!；演示管理员：admin@mcs.local / Admin123!。当前为开发配置，演示凭据仍保留，正式使用前应替换。
- 当前 CA 已导入本机用户 NSS 数据库及 Snap Chromium NSS 数据库。其他设备需导入 infra/certs/jetson-local-ca.pem；不要传私钥。CA 证书下载入口：http://192.168.50.11/local-ca.crt 。
- IP 变化后应重签包含新 IP 的服务器证书。

```bash
cd /home/nvidia/Documents/depression-system
bash scripts/orin-nx-stack.sh ps
bash scripts/orin-nx-stack.sh logs --tail=100 multimodal-service
bash scripts/orin-nx-stack.sh stop
bash scripts/orin-nx-stack.sh up -d --no-build
bash scripts/open-orin-nx-browser.sh
```

当前对话进程沿用旧用户组，通过 sg docker 执行上述容器命令；新登录终端可直接执行。不要用旧系统 docker compose 或 scripts/jetson-stack.sh 管理本机配置，前者不支持正确的 !override，后者没有包含新增 Orin NX 配置。不要执行 down -v 删除业务卷。

## 内存、共享显存与存储

- 开发板：Jetson Orin NX，16GB 规格。Linux 实际可见物理内存 **15.29GiB**，交换空间约 **7.64GiB**。
- 这是集成 GPU：CPU、GPU 共用 DRAM，没有另一块可相加的独立显存。CUDA 同样报告约 15.29GiB 总共享内存。独立 CUDA 探测进程报告可用约 7.33GiB，但探测进程本身会创建 CUDA 上下文，该数值不用于计算项目独占显存。
- NVIDIA 原理说明：https://docs.nvidia.com/cuda/archive/12.0.1/pdf/CUDA-For-Tegra-AppNote.pdf
- NVMe 标称 **256GB**（原始设备 256060514304 字节），根分区约 **233GiB**。
- 部署后根分区已用 **54.48GiB**，普通用户可用 **165.89GiB**；剩余部分还包含文件系统保留空间。

为排除编译影响，所有镜像构建结束后，先停止整个项目并关闭诊断浏览器，再启动 GPU 部署、完成模型预热和预录音验收，最后测浏览器播放视频。没有清空 Linux 页缓存，也没有清空 swap。

| 阶段 | 整机内存占用 GiB | MemAvailable GiB | Swap 占用 GiB |
|---|---:|---:|---:|
| 项目全部停止，浏览器关闭 | 3.13 | 11.86 | 0.48 |
| CPU 情绪配置预热（参考） | 7.58 | 7.39 | 0.45 |
| GPU 后端预热，浏览器关闭 | 7.16 | 7.74 | 0.48 |
| GPU 后端 + GPU 浏览器播放视频 | 7.43 | 7.45 | 0.48 |

GPU 后端相对项目停止的整机内存增量约 **4.03GiB**。这些是短时快照，包含共享内存和宿主机状态变化，不是容量压测。MemAvailable 包含可回收缓存，不能把 MemFree 很低直接理解为内存不足。容器统计不一定完整归属 Jetson GPU 分配，因此以整机占用和 MemAvailable 判断容量。

最初部署前保存的粗略终端快照为：内存已用约 2.8GiB、可用约 12GiB、swap 为 0；磁盘已用约 34GiB、可用约 188GiB。与当前磁盘相比新增约 **20GiB**，包含源码、Git/LFS 缓存、模型和媒体、Docker 镜像、TensorRT 引擎与构建产物。最初数值已经四舍五入，不能据此计算精确增量。

Docker 当前报告镜像总大小 11.28GB（十进制），项目数据卷约 50.54MB。Git 目录约 4.4GiB，.codex-tmp 约 1.3GiB。各路径和镜像有共享层或缓存，不能简单相加推算根分区增量；未清理用户旧镜像或旧 ros 容器。

## 浏览器 GPU 与视频解码

浏览器为已安装的 Chromium 140.0.7339.127。使用本机 X11 图形桌面、独立配置进行测试，没有靠 headless 结果推断桌面加速，也未关闭 Chromium sandbox、未忽略证书错误、未修改默认浏览器。

| 检查项 | 默认 Snap 启动 | 项目专用启动器 |
|---|---|---|
| 实际渲染器 | SwiftShader 软件渲染 | NVIDIA Tegra Orin / OpenGL 4.5 / 540.4.0 |
| GPU 图形合成 | disabled_software | enabled |
| GPU 光栅化 | disabled_software | enabled |
| Canvas、WebGL / WebGL2 | 软件 / 不可用 | enabled |
| 视频硬件解码 | disabled_software | disabled_software |
| 实际 VP9 解码器 | VpxVideoDecoder | VpxVideoDecoder |

专用脚本直接运行 /snap/chromium/current/usr/lib/chromium-browser/chrome，以宿主机图形环境运行同一二进制；Snap 包和系统驱动均保持不变。该差异证明启动环境会影响 GPU 初始化，但本次没有进一步定位到某一 Snap 库或权限规则。

两次测试用同一数字人 greeting-001.webm（1920×1080 VP9），1280×800 浏览器窗口、640×360 视频显示区域，静音循环；等待约 3 秒后采样约 20 秒。它是实际项目视频播放测试，未同时采集摄像头或录音，不代表完整问诊负载。

| 短时测量 | 软件启动 | GPU 启动 |
|---|---:|---:|
| 浏览器 CPU，单核=100% | 118.9% | 99.1% |
| 浏览器进程 PSS，MiB | 468.5 | 464.8 |
| 累计呈现帧 / 丢帧 | 693 / 0 | 693 / 0 |

该窗口浏览器 CPU 降低约 16.6%，两者均无丢帧；这不是长时间基准测试，也不意味着所有页面都能获得同样提升。视频仍由 CPU 解码，不能把 GPU 合成已启用表述为视频硬解已启用。Chromium 对两类功能的区别见 https://www.chromium.org/developers/design-documents/video/ 。

## 底层环境与升级决定

保留 Ubuntu 22.04.5、L4T R36.4.3、CUDA 12.6、TensorRT 10.3.0 和 NVIDIA PyTorch 2.5.0a0+872d972e41.nv24.08。GPU 张量实际运算通过。CUDA 12.6 / TensorRT 10.3 符合 JetPack 6.2 官方计算栈：https://developer.nvidia.com/embedded/jetpack-sdk-62 。

仅执行 apt 的只读模拟，没有执行 apt upgrade / full-upgrade，也没有修改 hold 或软件源。当前缓存索引有 918 个可升级包；模拟 upgrade 会升级 876 个，其中 74 个 NVIDIA 相关包，包含 L4T 36.4.3 → 36.4.7、内核、bootloader、摄像头和多媒体组件。建议先保持项目基线，安全更新另行筛选并测试；涉及 Jetson 底层的更新安排备份和维护窗口。浏览器安全更新也应单独计划，并在更新后复测图形与视频路径，而非长期冻结所有组件。

确实需要升级的是 Compose：系统原有 2.21.0 会把带 !override 的端口配置错误合并。项目内安装 2.32.4 并核验官方 SHA256，未升级系统 Docker。官方最低要求为 2.24.4：https://docs.docker.com/reference/compose-file/merge/ 。

新增 Dockerfile.orin-nx 在容器内补齐 MediaPipe 0.10.18、JAX 0.4.33 和依赖约束；torchaudio 2.5.0 针对宿主机 NVIDIA torch 从源码编译，安装在项目 .codex-tmp/gpu-python 中。没有覆盖宿主机现有 torch、CUDA 或 TensorRT。新增 Compose 配置加入日志轮转、Redis 命名卷与 AOF。

## 验收范围与保留产物

已通过：

- Git LFS 全部展开及 fsck；Compose 有效合并、脚本语法、make compose-config、make phase-check。phase-check 提示宿主机没有 FastAPI，容器应用运行不受影响。
- CPU 配置完整 smoke：10 个应用健康接口、HTTPS、WebM、注册、登录、个人资料、问诊创建与启动、五模态预热、文本实际推理。
- GPU 配置同样链路，加 4 秒预录音上传、MinIO 原音频和归一化 WAV、CUDA Dolphin 转写、语音及文本情绪分析。
- 实际人脸接口识别到 1 张脸；姿态接口积累 8 帧后返回有效四分类结果。
- 四个 TensorRT 引擎在本板生成，模型和引擎哈希验证通过；相同合成输入 CPU/GPU 均返回有限值且分类一致。姿态 FP32，其他模态混合 FP16。该检查验证数值与运行路径，不验证模型准确率。
- 容器内 NVIDIA torch、torchaudio 重采样、MediaPipe、TensorRT、Dolphin 导入与 CUDA 张量计算。
- 停止 / 重新启动项目成功，restart=unless-stopped；Docker 服务开机启动已启用。尚未重启整机验证。
- 独立图形浏览器以可信 HTTPS 打开真实前端、渲染页面并播放项目视频。

尚未验证：实体摄像头、麦克风、BLE EEG 真机采集；多用户长时间压力测试；整机断电重启与备份恢复演练。EEG 未注入模拟流，ready=200 不表示已经有真机 EEG 数据。followup-service 当前只注册健康接口，容器正常不等于随访业务已实现。

测试账号均明确标记为非真实患者，测试记录保留于本机数据库；未访问真实患者记录。GPU 音频验收账号为 jetson-deployment-smoke-56917ead@mcs.local。

证书、项目内工具、GPU Python 包、引擎及验收数据存放于 infra/certs 与 .codex-tmp，未提交 Git。**不要清理 .codex-tmp：当前运行需要其中的 GPU Python 包、Compose 和 TensorRT 引擎。**

原始 JSON 和 tegrastats 记录：.codex-tmp/resource-audit/；其余验收日志位于 .codex-tmp/。临时诊断浏览器已关闭，调试端口不作为日常启动配置。
