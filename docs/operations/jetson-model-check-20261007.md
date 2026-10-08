# 多模态模型加载与推理验收（2026-10-07）

检查时间：2026-10-07 11:42–11:45（Asia/Shanghai）。本轮针对正在运行的 Jetson 部署检查，没有修改业务代码、模型文件或部署配置，没有重启服务。

结论：文本、语音情绪、人脸、姿态的实际接口推理通过，Dolphin 转写全链路通过；四个 TensorRT 引擎可在当前容器环境执行 GPU 推理。EEG 服务中的模型已加载，同一模型的隔离合成特征推理通过，但运行服务尚未接收到 EEG 设备数据流。

## 检查结果

| 模态 / 模型 | 加载及实际使用检查 | 结果 |
| --- | --- | --- |
| 文本情绪 | 实际 `/api/v1/non-eeg/text-emotion/infer`，输入明确标记的测试文本 | code=0，二分类结果及分数有限，HTTP 总耗时约 31 ms |
| 语音情绪 | 实际 `/api/v1/non-eeg/audio-emotion/infer`，4 秒仓库数字人问候音频 | code=0，四分类结果及分数有限，HTTP 总耗时约 82 ms |
| 人脸情绪 | 从仓库数字人视频提取 640×360 图像，调用实际 frame-infer 接口 | status=ok，检测到 1 张脸，七类分数有限，HTTP 总耗时约 63 ms |
| 姿态情绪 | 同一项目素材调用实际 frame-infer 接口，使用独立 session/turn 连续输入 8 帧 | 进入有效四分类，返回 8 帧及 MediaPipe 33→21 关节适配信息，最后一帧 HTTP 总耗时约 82 ms |
| Dolphin ASR | 新合成账号经 LAN HTTPS 创建问诊，五模态预热、上传预录 WAV、轮询结果 | completed，provider=dolphin，转写非空，原音频和归一化 WAV 已存储 |
| EEG | 运行服务 readiness 的 model_loaded=true；隔离进程加载同一模型，执行特征归一化、聚合、特征选择、scaler、SVM 分类 | 加载及推理通过，概率为有限值；未接收真机流 |

以上接口耗时是已运行服务的单次采样，包含 HTTP、解码、检测及相关前处理，不是纯模型耗时，也不代表并发性能。分类标签与置信度只用于验证数值和协议，不能用合成素材判断模型准确率。

## GPU 引擎验证

在正在运行的 `multimodal-service` 容器中启动独立检查进程，逐个加载当前挂载的 `.plan`，通过应用的 `_TensorRTSession.run` 实际执行，不同时保留四套临时引擎。每次执行后释放引擎及临时 CUDA 缓存。

环境：torch `2.5.0a0+872d972e41.nv24.08`、TensorRT `10.7.0`，`torch.cuda.is_available()=true`。

| 引擎 | 输入形状 | 输出形状 | 有限值 | 本次 CPU fallback |
| --- | --- | --- | --- | --- |
| text_emotion | input_ids / attention_mask：1×32 | 1×2 | 是 | 无 |
| audio_emotion | input_values：1×64000 | 1×4 | 是 | 无 |
| face_emotion | input：1×1×48×48 | 1×7 | 是 | 无 |
| pose_emotion | sequence：1×96×21×4 | 1×4 | 是 | 无 |

该检查证明当前挂载引擎可反序列化并在 GPU 执行。它不直接读取 Uvicorn 进程内的缓存对象，因此不提供每个线上请求实际 backend 的逐请求遥测；实际业务接口的成功和独立 GPU 验证分别记录。应用配置启用 TensorRT，输入超出引擎 profile 时实现允许回退 ONNX CPU。

## EEG 模型与采集边界

运行服务检查前后均显示：

```text
model_loaded=true
model_name=SVM_rbf_C1.5
model_version=v20_window52_trialagg_mss_3class
provider=redis_stream
provider_started=true
device_status=waiting_for_stream
last_error=null
last_transport_at=null
last_packet_seq=null
```

模型要求每帧 52 个特征，聚合后 156 个特征，选择 110 个特征送入 scaler/SVM。隔离进程依据当前运行配置使用 10 个合成特征帧，调用实际 `_infer_window_locked` 推理路径，返回三类有限分数。

隔离进程没有启动 transport，没有发布 Redis EEG 数据、绑定真实问诊轮次或保存 EEG 测试结果。该检查不验证电极接触、蓝牙/桥接程序、原始波形到特征提取及真实 EEG 整条采集链路。

当前 `EEG_REQUIRE_TRANSPORT_FOR_READY=false`，且 waiting_for_stream 属于实现允许的 transport 状态。readiness=200 不代表已有真实 EEG 数据进入；运行服务仍在等待设备数据流。真机联调应观察 `last_transport_at`、`last_packet_seq` 更新及问诊轮次内有效 EEG 结果。

## ASR 新测试记录

- 合成账号：`jetson-deployment-smoke-dbe04e84@mcs.local`，明确标记为非真实患者。
- 问诊 session：`19e05a95-4db3-4390-b2b2-aca8307da4ca`。
- multimodal session：`127547be-1c0f-43d1-a896-57af6c503c16`。
- WAV 时长 4000 ms；记录创建至最后更新约 0.99 秒，此值不是纯 ASR 耗时。
- 只检查该合成记录的状态、provider、转写非空标志及存储字段；没有读取真实用户的音频或转写。

测试后 14 个容器仍运行，已配置健康检查的容器保持 healthy。原始检查脚本、JSON、日志和项目素材截帧位于 `.codex-tmp/model-check/`，目录权限 0700，已被 Git 忽略。
