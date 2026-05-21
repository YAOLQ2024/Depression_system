# multimodal-service Docker / GPU 改造方案

## 1. 背景

当前 `multimodal-service` 已经承担：

- Dolphin ASR
- 语音情绪识别
- 面部情绪识别
- 姿态识别

但开发与联调阶段存在两个明显问题：

1. Docker 重建成本过高  
   `torch`、`torchaudio`、`dataoceanai-dolphin`、`opencv`、`mediapipe` 等依赖体积大，导致镜像构建慢、镜像体积大。

2. GPU 未进入当前容器  
   当前 PC 宿主机可见 NVIDIA GPU，Docker 也具备 `nvidia` runtime，但 `compose-multimodal-service-1` 未申请 GPU，实际运行仍是 CPU。

本方案目标是在**不破坏现有主链路**的前提下，同时解决：

- 日常开发重建慢
- 多模态联调不能方便启用 GPU
- 后续 Jetson / Orin 迁移缺乏清晰边界

---

## 2. 改造目标

### 2.1 总目标

形成一套“**默认可快速开发 + 可选 GPU 加速 + 后续可扩展到 Jetson**”的结构。

### 2.2 具体目标

1. `multimodal-service` 默认仍可 CPU 跑通完整流程。
2. 业务代码变更后尽量复用 Docker 依赖缓存，不反复安装重依赖。
3. 需要联调 ASR / 多模态性能时，可通过 Compose override 启用 NVIDIA GPU。
4. 不把 PC x86 CUDA 方案和 Jetson ARM64 方案混在同一份 Dockerfile / compose 中。

---

## 3. 推荐方案

推荐采用三层结构：

1. **Docker 构建优化**
2. **CPU / GPU 双运行入口**
3. **Jetson 独立适配**

### 3.1 Docker 构建优化

`multimodal-service` 仍然保持一个服务、一个容器，但优化 Dockerfile 分层。

建议分为四层：

1. `apt` 系统依赖层  
   例如：`ffmpeg`、`libgl1`、`libglib2.0-0`、`libgomp1`

2. 重型 ML 依赖层  
   例如：
   - `torch`
   - `torchaudio`
   - `dataoceanai-dolphin`
   - `onnxruntime`
   - `opencv-python-headless`
   - `mediapipe`

3. 轻量 Python 业务依赖层  
   例如：
   - `fastapi`
   - `sqlalchemy`
   - `psycopg`
   - `minio`
   - `alembic`

4. 业务代码层  
   `COPY . .`

这样做的效果是：

- 第一次构建仍然较慢
- 但后续只改业务代码时，前 1-3 层可以稳定复用缓存
- 不会因为小范围代码改动反复重装 `torch`

### 3.2 CPU / GPU 双运行入口

保留：

- `infra/compose/docker-compose.dev.yml`

作为默认开发入口：

- 通用
- 稳定
- CPU 可跑通
- 不要求所有开发者本机都有 NVIDIA GPU

新增：

- `infra/compose/docker-compose.gpu.yml`

只覆盖 `multimodal-service` 的 GPU 运行参数，例如：

- `runtime: nvidia` 或 `gpus: all`
- `NVIDIA_VISIBLE_DEVICES=all`
- `NVIDIA_DRIVER_CAPABILITIES=compute,utility`
- `ASR_DEVICE=cuda`

启动方式：

```powershell
docker compose -f .\infra\compose\docker-compose.dev.yml -f .\infra\compose\docker-compose.gpu.yml up -d
```

这样可以做到：

- 默认 CPU 开发链路不受影响
- 需要 GPU 时再叠加 override

### 3.3 Jetson / Orin 独立适配

PC NVIDIA GPU 环境与 Jetson / Orin 不应共用同一套镜像与运行策略。

建议后续单独增加：

- `infra/compose/docker-compose.jetson.yml`
- `services/multimodal-service/Dockerfile.jetson`

理由：

- PC 通常是 `x86_64 + CUDA`
- Jetson / Orin 通常是 `ARM64 + JetPack`
- 依赖源、基础镜像、GPU 栈、系统库可能都不同

因此 Jetson 适配应当作为独立阶段，不在当前 PC 开发方案中强行混合。

---

## 4. 优点

### 4.1 适配当前项目现状

当前最重、最需要 GPU、最容易拖慢构建的服务就是 `multimodal-service`。  
因此优先对它进行 Docker/GPU 改造，收益最大，影响面也可控。

### 4.2 提升开发效率

把依赖层与业务代码层拆开后，日常只改：

- `app/services/...`
- `app/api/...`
- `app/schemas/...`

这类代码时，不需要每次重新安装重依赖。

### 4.3 保持团队兼容性

默认 compose 仍能让：

- 无 GPU 开发者
- 普通 CI
- 只做前后端流程联调的人

继续按 CPU 模式工作。

### 4.4 GPU 能力按需启用

GPU 只在需要时启用，不把 GPU 环境要求强加给每位开发者。

### 4.5 为板端适配预留清晰边界

Jetson / Orin 与 PC 方案拆开后，后续迁移不会反复污染当前 PC 开发配置。

---

## 5. 缺点与代价

### 5.1 文件数量增加

会新增或调整：

- `Dockerfile`
- `docker-compose.gpu.yml`
- 后续的 `Dockerfile.jetson`
- 后续的 `docker-compose.jetson.yml`

维护成本略有增加。

### 5.2 需要维护 CPU / GPU 两套运行验证

后续需要确认：

- CPU 模式可运行
- GPU 模式也可运行

否则可能出现“CPU 正常、GPU 异常”的分叉问题。

### 5.3 不是一次性解决所有性能问题

该方案能显著改善构建与运行方式，但不能自动解决：

- ASR 对真实浏览器录音的转写质量问题
- 模型偏置问题
- GPU 推理性能调优问题

它解决的是**工程运行方式**，不是**模型效果本身**。

---

## 6. 对当前项目的适配性评估

结论：**适配，且推荐采用。**

理由如下：

1. 当前瓶颈集中在 `multimodal-service`
2. 当前 PC 宿主机已具备 NVIDIA GPU
3. Docker 已具备 `nvidia` runtime
4. 当前容器尚未申请 GPU，说明主要缺的是运行配置，而不是硬件条件
5. 当前项目仍处于频繁改动期，比起“最终生产式封装”，更需要“快速改、快速试、按需开 GPU”

因此该方案与当前阶段非常匹配。

---

## 7. 建议的实施顺序

### Phase 1：Docker 分层优化

目标：

- 先解决“改一点代码就重装大依赖”的问题

实施项：

1. 重新整理 `services/multimodal-service/Dockerfile`
2. 将重依赖与轻依赖分层
3. 确认 `.dockerignore` 不把大模型权重带进镜像上下文
4. 构建一次，验证缓存是否能稳定命中

### Phase 2：GPU override

目标：

- 不改默认开发链路的前提下，让 `multimodal-service` 可见 GPU

实施项：

1. 新增 `infra/compose/docker-compose.gpu.yml`
2. 只对 `multimodal-service` 增加 GPU 运行参数
3. 通过下列方式验证：
   - `docker inspect ... DeviceRequests`
   - `ls /dev/nvidia*`
   - `torch.cuda.is_available()`

### Phase 3：运行验证

目标：

- 验证 GPU 模式下 `multimodal-service` 真正使用 GPU

实施项：

1. 重新启动：

```powershell
docker compose -f .\infra\compose\docker-compose.dev.yml -f .\infra\compose\docker-compose.gpu.yml up -d --build multimodal-service
```

2. 在容器中验证：
   - `torch.cuda.is_available() == True`
   - `torch.cuda.device_count() >= 1`
3. 观察 Dolphin ASR / 情绪识别推理耗时变化

#### Phase 3 当前验证结果

当前 Phase 3 已完成第一轮 CPU / GPU 实测，结论如下：

1. Docker GPU override 已生效  
   通过 `docker inspect` 可见 `DeviceRequests` 已申请 GPU，`Runtime` 为 `nvidia`。

2. 容器内 PyTorch 已可见 GPU  
   已验证：
   - `torch.cuda.is_available() == True`
   - `torch.cuda.device_count() == 2`
   - 设备名为 `NVIDIA GeForce RTX 3090`

3. Dolphin ASR 已按 GPU 模式运行  
   `ASR_DEVICE=cuda` 生效后，`asr_runtime` 解析出的设备为 `cuda`。

4. 当前 ONNX 非 EEG 模型已可运行在 GPU  
   通过切换到 `onnxruntime-gpu` 并补齐 NVIDIA 运行时动态库路径后，当前容器内 `onnxruntime` 可见 provider 为：
   - `TensorrtExecutionProvider`
   - `CUDAExecutionProvider`
   - `CPUExecutionProvider`

   且已实测确认以下 engine 的 session provider 为：
   - 文本情绪识别：`CUDAExecutionProvider, CPUExecutionProvider`
   - 语音情绪识别：`CUDAExecutionProvider, CPUExecutionProvider`
   - 面部情绪识别：`CUDAExecutionProvider, CPUExecutionProvider`
   - 姿态识别：`CUDAExecutionProvider, CPUExecutionProvider`

5. HTTP 服务层联调已通过  
   在 CPU / GPU 两种模式下，均已成功完成：
   - 创建 `multimodal session`
   - 提交 `audio-turn`
   - 返回 `speech_emotion`
   - 返回 `transcript_text`
   - 更新 `live_state_payload`

6. 当前 GPU 收益已覆盖 ASR 与非 EEG ONNX 推理  
   当前 GPU 模式下：
   - Dolphin ASR 已使用 CUDA
   - 语音情绪识别已进入 CUDA provider 路径
   - 面部情绪识别已进入 CUDA provider 路径
   - 姿态识别已进入 CUDA provider 路径

   也就是说，`multimodal-service` 当前承载的主要推理能力已经全部具备 GPU 运行条件。

7. 当前性能结论仍应谨慎解读  
   现阶段测试基于小样本与短音频，首轮请求耗时仍显著受模型加载与初始化影响。  
   因此当前更可靠的结论是：
   - GPU 可见性已验证通过
   - Dolphin ASR 的 CUDA 路径已验证通过
   - 非 EEG ONNX 模型的 CUDA provider 路径已验证通过
   - 仍需基于真实业务样本继续做 CPU / GPU 耗时对比

8. 暴露出的一个现有限制  
   当前 `multimodal_sessions.flow_run_id` 字段长度为 `varchar(36)`，如果上层传入更长的 flow 标识，会导致数据库写入失败。  
   后续若要支持更长的业务 flow 标识，需要单独补迁移扩容该字段。

### Phase 4：Jetson 方案独立推进

目标：

- 在 PC 方案稳定后，再做板端适配

实施项：

1. 新增 `Dockerfile.jetson`
2. 新增 `docker-compose.jetson.yml`
3. 根据 JetPack / ARM64 环境单独适配依赖

---

## 8. 具体文件改造建议

### 8.1 当前阶段应改造

- `services/multimodal-service/Dockerfile`
- `services/multimodal-service/requirements.txt`  
  视情况拆分为：
  - `requirements-heavy.txt`
  - `requirements.txt`
- `infra/compose/docker-compose.gpu.yml`

### 8.2 当前阶段暂不改造

- `consultation-service`
- `gateway-service`
- `assessment-service`

原因：

- 这些服务不以 GPU 为主要诉求
- 也不是当前构建体积的主要来源

---

## 9. 推荐结论

推荐采用本方案，并按以下优先级执行：

1. 先优化 `multimodal-service` Docker 构建分层
2. 再新增 GPU compose override
3. 先在 PC 上跑通 CPU / GPU 双模式
4. 最后再单独推进 Jetson / Orin 适配

一句话总结：

**当前最合适的方向，不是直接把全部环境一次做复杂，而是把 `multimodal-service` 改造成“默认快速开发、按需启用 GPU、后续可分支到 Jetson”的结构。**
