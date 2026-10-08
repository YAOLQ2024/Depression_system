# Jetson 四模态模型升级与验收（2026-10-07）

## 版本与保留内容

- 分支 `feature/zhurui`，同步到 `11478db7ebc883ed93641e2eb4c5da6f2df77e80`。
- Codeup SSH 别名配置完成，连接测试成功；配置与私钥权限 600、公钥权限 644。
- 执行 `git pull --tags origin feature/zhurui`、`git lfs pull` 和 `git lfs fsck`；完整性通过。
- 板端原有 HTTPS、证书、前端和运行时修复均保留；本次部署改动尚未提交或推送。
- 升级前工作区补丁、未跟踪文件、SSH 配置、Compose 配置、旧镜像 ID 与提交号保存在 `.codex-tmp/model-upgrade/`，权限 700。旧本板引擎保留在 `.codex-tmp/tensorrt/`。

## 正式模型与输入契约

| 模态 | ONNX 字节数 | 输出类别 | 输入要求 | 本板执行方式 |
| --- | ---: | ---: | --- | --- |
| 文本 | 409293552 | 2 | 原 tokenizer，原分类逻辑 | 本板既有 TensorRT 引擎重新核对 CPU 输出 |
| 音频 | 648988390 | 9 | 单声道 16 kHz，动态长度 | 新建 TensorRT，混合 FP16 |
| 人脸 | 343494605 | 7 | BGR→RGB，224×224，均值/标准差 0.5 | 新建 TensorRT，混合 FP16 |
| 姿态 | 14033670 | 4 | MediaPipe 33→21 点，4 通道，8～96 帧 | 新建 TensorRT，FP32，禁用 TF32 |

正式 ONNX 路径仍为 `services/multimodal-service/runtime-assets/models/`。全部四个 ONNX 哈希与 [交付模型清单](../../deliverables/four_modal_onnx_upgrade_v1_20261003/model_manifest.json) 一致。交付材料与 [原板端部署清单](../../deliverables/four_modal_onnx_upgrade_v1_20261003/JETSON_DEPLOYMENT.md) 已随 Git 同步。

## 已确认并修复的问题

1. 旧音频、人脸、姿态引擎不能对应新 ONNX：先移除旧挂载，关闭 TensorRT，完成 CPU 验证后才切换本板新引擎。
2. 姿态 FP16 引擎在 8 帧时正常，但 96 帧随机有限值输入输出 NaN：拒绝启用，重新使用 FP32 构建。修复后 8/96 帧均为有限值，且与 CPU 输出一致。无效引擎与日志仅留在私有验收目录。
3. 前端缺少音频 `other`、`unknown` 的中文展示：补充为“其他”“未知”；榜单接受动态类别。
4. 风险规则仍使用 `ang`，新音频返回 `angry`：补充同义匹配，覆盖默认规则和自定义规则；原有权重与类别政策保留。新增音频 fear/disgust 不会自动被加入负性标签集合，这属于后续规则校准范围。
5. CPU 启动不应依赖 plan 已存在：GPU 引擎挂载拆到独立 Compose 覆盖配置，默认新板使用 CPU。
6. 本板引擎独立挂载 `/app/board-engines`，不在 ONNX 目录创建 plan 占位文件；引擎超出输入范围时明确回退到原始 ONNX 路径。
7. GPU 启动前检查 ONNX、plan 哈希和 L4T 版本，避免模型更新继续启动不匹配的引擎。

## 验证证据

- 实际容器 ONNX Runtime 1.20.1：交付脚本验证全部哈希、模型输入输出和旧 plan 清理状态通过。
- CPU 原始图验证：文本长度 4/32/256，音频 8000/16000/32000/64000/160000 采样点，人脸 RGB 224×224，姿态 8/96 帧；输出维度、有限值均通过。
- GPU 与同一输入的 CPU 对比：12 个输入案例，首选类别均一致，无预期范围内的 CPU 回退。最大概率绝对差：文本 0.001366、音频 0.019262、人脸 0.001154、姿态约 2.48e-10。此为有限输入契约验证，不是数据集准确率评测。
- 文本 257 token 超出引擎上限 256，实际 ONNX CPU 回退成功，输出有限的 2 类结果。
- `multimodal-service` 完整 pytest 32 项通过；风险标签回归 13 项通过。测试依赖临时安装，EEG 单元测试关闭 Redis 共享缓存，未写入真实设备流。
- 前端正式 Docker 构建通过；Compose 验证、`make phase-check`、Python 语法检查通过。宿主机未安装 FastAPI；实际 FastAPI、ORT 与 pytest 检查均在容器执行。
- CPU 和最终 GPU 两个阶段均通过实际浏览器 HTTPS 验收：严格证书校验、登录、准备页设备授权、摄像头图像上传、MediaRecorder 音频上传、MinIO、ASR、SSE、视频播放、后台登录和退出，脚本错误与请求失败均为 0。
- 浏览器验收使用模拟摄像头和录音源；其他局域网客户端的证书安装与物理设备授权仍按 [访问说明](lan-client-access.md) 操作。
- EEG 模型 `SVM_rbf_C1.5 / v20_window52_trialagg_mss_3class` 已加载，等待真实 Redis 设备流；本次未模拟硬件流。

## 30 分钟并发与资源记录

四模态接口每轮并发发送，目标周期 2 秒，包含文本预处理、音频解码、人脸检测和 MediaPipe 姿态处理。姿态保持同一测试窗口，持续覆盖到完整 96 帧。

2026-10-07 15:28:58～15:58:59（北京时间），连续 **1801.35 秒**，完成 **900 轮、3600 次请求**，失败 **0**；服务重启 **0**、OOM **0**，最终状态健康。

| 模态 | 请求数 | P50（ms） | P95（ms） | 最大（ms） |
| --- | ---: | ---: | ---: | ---: |
| 文本 | 900 | 86.26 | 109.79 | 146.92 |
| 音频 | 900 | 91.49 | 115.10 | 148.96 |
| 人脸 | 900 | 110.36 | 135.50 | 159.34 |
| 姿态 | 900 | 118.10 | 140.25 | 165.22 |

- 主机 RAM 使用峰值约 **6.35 GiB**（`MemTotal - MemAvailable`），可用内存最低约 **1.09 GiB**；tegrastats RAM 峰值 **6353 MiB**，两者统计口径不同。
- 服务进程 NVMAP 分配峰值 **1617644 KiB，约 1.54 GiB**；在监测中保持稳定。测试末 Docker 显示多模态容器内存约 **2.04 GiB**，这不是容器峰值记录。
- Swap 使用峰值约 **2.70 GiB**；本次没有调整内存或交换区配置。
- CPU 温度最高 **50.031℃**，GPU/TJ 最高 **50.468℃**；未观察到热降频。GPU 时钟采样值为 **306～714 MHz**，采样从测试第约 9 分钟开始；频率随负载变化，不能据此把所有降低频率都认定为热降频。
- 这是固定测试素材、四模态每 2 秒一轮的并发验收，包含已加载的 ASR 模型驻留，但未模拟多用户持续高频请求或连续 ASR 转写压力。

完整版本、引擎哈希、CPU/GPU 差异与验收数字见 [机器可读验收报告](jetson-four-modal-upgrade-20261007.json)。

原始记录位于 `.codex-tmp/model-upgrade/`：`stability-rounds.jsonl`、`stability-summary.json`、`stability-resources.json`、`tegrastats.log`、`gpu-memory.jsonl`、`gpu-clocks.jsonl`。临时监测进程已关闭，正式服务保持运行。

Jetson 使用统一内存：记录主机可用内存、tegrastats RAM，以及服务进程的 NVMAP 分配峰值；这些指标不能相加当作独立 RAM/显存总量。NVMAP 记录反映分配量，不等同于所有 GPU 工作负载的精确独立显存占用。参考 [NVIDIA tegrastats 文档](https://docs.nvidia.com/jetson/l4t/Tegra%20Linux%20Driver%20Package%20Development%20Guide/AppendixTegraStats.html)。

## 软件与构建材料

- Jetson Orin Nano，L4T 36.4.3，CUDA runtime 12.6.77，TensorRT 10.7.0.23。
- ORT 1.20.1 的可用 provider 仍为 CPU；GPU 情感推理由板端 `_TensorRTSession` 直接调用 TensorRT/CUDA 实现。实际引擎执行和数值对比证明 GPU 链路，不以 ORT provider 名称代替验证。
- MediaPipe 沿用本板兼容的 0.10.18，33→21 点适配保持；未为匹配交付机版本而强制降级。
- 容器 Python 3.10.12、PyTorch 2.5.0a0+872d972e41.nv24.8、torchaudio 2.5.1a0+1661daf、transformers 4.46.2、FastAPI 0.115.0、Dolphin 20260513。
- 最终多模态镜像 ID：`sha256:dc9442aa757f90fc8f06bb64c1b8840b0c72892475b3b8eeba86e3426cde5209`。
- 每个引擎的 SHA-256、ONNX SHA-256、完整构建命令和板端 L4T 记录在 `.codex-tmp/tensorrt-upgrade-20261007/<modality>/manifest.json`。
- 容器镜像 ID、完整 plan 清单和 CPU/GPU 对比结果见私有 `image.txt`、`plans.json`、`parity/trt-parity.json`。

## 板端操作

当前板已通过验收，使用 `.codex-tmp/tensorrt.enabled` 标记保持 GPU 配置。

```bash
# 正常启动，自动选择本板已验证的 GPU 配置
./scripts/jetson-stack.sh up -d

# 更新模型后先切回 CPU；不依赖任何板端 plan
MCS_TENSORRT_ENABLED=false ./scripts/jetson-stack.sh up -d --no-deps multimodal-service

# 本板构建新引擎（默认姿态 FP32，其余混合 FP16）
python3 scripts/jetson-build-engines.py
python3 scripts/jetson-verify-engines.py

# 完成 CPU/GPU 输出验证后启用
touch .codex-tmp/tensorrt.enabled
./scripts/jetson-stack.sh up -d --no-deps multimodal-service
```

长期保持 CPU 模式可删除本地启用标记再执行启动命令。移植其他板时不复制 `.codex-tmp` 引擎和启用标记，先按交付清单执行 CPU 验证。旧 ONNX 与回退提交仍保留在 Git/LFS；回退前使用私有工作区备份恢复板端改动并重新验证相应本板引擎。

本次没有清理 Ollama、旧模型资源或执行磁盘/内存调整；磁盘余量约 2 GiB，按用户要求留待后续处理。
