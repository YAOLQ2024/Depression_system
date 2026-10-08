# 非 EEG 四模态模型解读与升级对照报告

报告日期：2026-10-08（Asia/Shanghai）。适用项目：depression-system / Jetson Orin Nano。

本报告汇总文本、音频、人脸和姿态的模型、文件大小、输入输出、数据关系及验收边界。EEG 不展开说明，仅在下游默认融合权重中保留其位置。

## 1. 对照基线与主要变化

“原来模型”指本次替换前的提交 `a36ff6d847dc9a6b7f3585274fdff7fbef13dff6`；“当前模型”指模型升级提交 `11478db7ebc883ed93641e2eb4c5da6f2df77e80` 及板端部署修复。旧模型大小来自该提交的 Git LFS 记录，并与本地缓存实物核对；旧模型结构与张量契约来自真实 ONNX 图和旧适配器，不根据文件名猜测来源。

- 文本：保留原 BERT 结构二分类模型、tokenizer 和分类逻辑。
- 音频：Wav2Vec2 结构四分类替换为 emotion2vec_plus_large 九分类。
- 人脸：灰度 48×48 的残差 CNN 七分类替换为 RGB 224×224 的 ViT 七分类；类别索引顺序发生变化。
- 姿态：BiLSTM + ST-GCN + Stacker 的内部融合模型替换为 AGCN seed72；保持 21 点、4 通道和四分类接口。
- 浏览器采集、Dolphin 转写、统一会话/轮次汇总和下游风险服务的总体数据关系延续原有结构。

## 2. 原模型与当前模型对照

### 2.1 模型名称、ONNX 大小及变化

| 模态 | 原来模型 | 原 ONNX 大小 | 当前模型 | 当前 ONNX 大小 | 大小变化 |
| --- | --- | --- | --- | --- | --- |
| 文本 | BERT 结构中文情绪二分类；具体原始微调仓库未记录 | 409,293,552 B / 390.33 MiB | 保留原模型，未替换 | 409,293,552 B / 390.33 MiB | 不变 |
| 音频 | Wav2Vec2 结构情绪四分类；具体来源仓库未记录 | 378,512,173 B / 360.98 MiB | iic/emotion2vec_plus_large，九分类 | 648,988,390 B / 618.92 MiB | +257.95 MiB，约 1.71 倍 |
| 人脸 | 残差 CNN / ResNet 风格七分类；具体训练来源与骨干版本未记录 | 44,675,165 B / 42.61 MiB | mo-thecreator/vit-Facial-Expression-Recognition，ViT 七分类 | 343,494,605 B / 327.58 MiB | +284.98 MiB，约 7.69 倍 |
| 姿态 | BiLSTM + ST-GCN 两路分类，经可学习 Stacker 融合，四分类 | 8,876,594 B / 8.47 MiB | AGCN seed72，四分类 | 14,033,670 B / 13.38 MiB | +4.92 MiB，约 1.58 倍 |

原四模型 ONNX 合计 **802.38 MiB**，当前合计 **1,350.22 MiB，约 1.32 GiB**，增加 **547.84 MiB**。这里只计算四份 ONNX，不包含 Git LFS 缓存、交付目录副本、TensorRT 引擎、Dolphin 或其他辅助模型。

旧姿态模型的 Stacker 融合只发生在姿态模型内部，不能与下游“四模态及 EEG 的风险融合”混为一谈。

### 2.2 输入输出契约对照

| 模态 | 原模型输入 | 当前模型输入 | 原模型输出 | 当前模型输出 |
| --- | --- | --- | --- | --- |
| 文本 | input_ids、attention_mask；int64 [B,L]；适配器最多 256 token | 不变 | logits [B,2] | logits [B,2] |
| 音频 | 16 kHz 单声道浮点波形；input_values [B,N] | 外部波形契约不变；归一化已纳入新 ONNX 图 | logits [B,4] | logits [B,9] |
| 人脸 | 灰度 float32 [1,1,48,48] | RGB float32 [B,3,224,224] | output [1,7] | output [B,7] |
| 姿态 | sequence float32 [B,T,21,4] | 不变；MediaPipe 33→21 点；至少 8 帧，窗口最多 96 帧 | probs [B,4] | probs [B,4] |

B 表示批大小，当前正常请求按单条处理；L 表示 token 数；N 表示采样点数；T 表示有效骨架帧数。ONNX 的动态批维度不代表本板 TensorRT 引擎支持任意批大小。

### 2.3 本板 TensorRT 引擎对照

| 模态 | 原本板引擎大小 | 当前实际使用引擎大小 | 当前精度 |
| --- | --- | --- | --- |
| 文本 | 197.72 MiB | 197.72 MiB | 混合 FP16；复用本板已验证引擎 |
| 音频 | 183.13 MiB | 312.89 MiB | 混合 FP16；按新 ONNX 重建 |
| 人脸 | 21.59 MiB | 167.57 MiB | 混合 FP16；按新 ONNX 重建 |
| 姿态 | 6.17 MiB | 15.53 MiB | FP32，禁用 TF32；按新 ONNX 重建 |

当前四份实际使用引擎合计约 693.71 MiB。ONNX 是迁移源文件，plan 是当前开发板的执行引擎；plan 不直接跨板复用。混合 FP16 不表示每一层都使用 FP16，也不是 INT8 量化。姿态引擎改用 FP32，是因为新 FP16 引擎在完整 96 帧测试中曾出现 NaN。

正式 ONNX 目录为 `services/multimodal-service/runtime-assets/models/`。当前板端实际引擎目录为 `.codex-tmp/tensorrt-upgrade-20261007/`，容器挂载至 `/app/board-engines`。文件大小不能直接等同于 RAM 或 GPU 内存需求。

## 3. 原来的数据关系

![升级前四模态数据关系](original-data-flow.svg)

旧版已经包含语音转写、文本情绪、声音情绪、人脸表情、骨架序列及统一汇总。本次升级前，人脸使用灰度小图，音频仅四类，姿态在模型内部组合 BiLSTM 与 ST-GCN 的分类结果。

## 4. 当前的数据关系

![当前四模态数据关系](current-data-flow.svg)

两张图表达数据依赖，不表示所有节点同时并发执行。正常录音上传主链先获得 Dolphin 转写，再完成后续声音和文本情绪分析。人脸与姿态来自同一摄像头采样图，后续预处理及分类彼此独立。

## 5. 四个模态的输入、处理与输出解读

### 5.1 文本：分析文字内容中的情绪倾向

输入通常来自 Dolphin 的转写文字，接口也可直接接收字符串。当前 BERT 词表有 21,128 个条目，词向量维度为 768。

处理链：文本清理 → tokenizer 分词及特殊标记 → 最多 256 token → input_ids / attention_mask → BERT 分类器 → 两个 logits → Softmax → 主标签及分数。

输出顺序固定为 `[negative, positive]`，前端展示“消极、积极”。它没有悲伤、恐惧、愤怒等细分类，也没有中性类别。服务另外生成的 negative_terms 是独立关键词匹配，不是 BERT 的输出。

256 token 不等于 256 个汉字。长回答的转写文本可以完整保存，但模型只分析截断后的输入。转写错误也可能传递到文本情绪结果。

### 5.2 音频：分析声音波形中的情绪

处理链：浏览器 MediaRecorder 录音 → WebM/Opus 等上传文件 → FFmpeg 转 16 kHz 单声道 WAV → float32 波形 → 新 ONNX 图内均值/方差归一化 → 声音特征提取 → 时间平均汇总 → 九个 logits → Softmax → 主标签和候选类别。

采样点数满足 `N = 16,000 × 时长（秒）`。五秒录音是 80,000 个采样点，进入模型的 float32 波形约 312.5 KiB；压缩上传文件大小不能代表模型输入大小。

适配器默认保留前四名候选，问诊服务整理为主类别、分数及前三名。unknown 是模型自身的类别，当前没有“分数低于某阈值自动变为 unknown”的逻辑。

本板音频引擎 profile 为 8,000～160,000 个采样点，即约 0.5～10 秒。上传接口允许最长 60 秒；超出引擎范围时会尝试回退 ONNX CPU，当前没有自动切成多个十秒片段的流程。

### 5.3 人脸：分析采样图中的面部表情

处理链：摄像头 JPEG → OpenCV BGR 图 → Haar 检测主要人脸 → 裁剪并补约十像素边缘 → BGR 转 RGB → 224×224 → 像素除以 255 → `(x-0.5)/0.5` → 通道重排 [1,3,224,224] → ViT → 七个 logits → Softmax。

灰度图仍用于 Haar 检测，但分类输入已改为 RGB。ViT 使用 16×16 图块处理 224×224 图像，并结合不同图块信息完成表情分类。

初次优先选择面积最大的脸，后续参考上一张图的脸中心位置。没有检测到脸时返回 no_face、零分和空分布，不能把 neutral 占位值理解为真实“中性表情”；汇总时会排除 no_face 样本。

原始适配器输出英文主情绪、中文名称和完整分布；问诊服务主标签使用中文，前三名候选保留英文。下游必须按标签语义匹配，不能依赖某个固定索引。

### 5.4 姿态：分析同一轮次的骨架序列

处理链：摄像头图 → MediaPipe 提取 33 点 → 每点记录 x/y/z/visibility → 同一 session/turn 累计有效骨架 → 33→21 点映射 → [1,T,21,4] → AGCN 空间图卷积与时间卷积 → 四类概率。

21 点包括躯干和头部五点、左右肩肘腕六点、左右髋膝踝六点，以及左右拇指和食指四点。骨盆、部分脊柱及颈部点通过中点或插值生成。模型内部将排列转换为 [B,4,T,21,1]；末尾 Softmax 已包含在 ONNX 中，适配器不重复转换。

不足八个有效骨架帧时返回 collecting，服务层显示待采集；没有人体时返回 no_pose。最多使用最近 96 帧，窗口按会话和轮次分开保存，轮次结束后清理。

前端默认约每 1.5 秒采样一次，上传未完成会跳过新采样，页面隐藏时暂停。仅按该周期估算，八帧约需十到十二秒，96 帧约需两分多钟；补帧、漏检及网络延迟会改变实际时间。这里不是摄像头 30 FPS 下的连续 96 帧。

## 6. 新旧标签索引对照

标签按输出张量位置从 0 开始排列。方括号中的顺序不可随意交换。

| 模态 | 原模型输出标签顺序 | 当前模型输出标签顺序 |
| --- | --- | --- |
| 文本 | [negative, positive] | [negative, positive]；不变 |
| 音频 | 原字典 [neu, hap, ang, sad]；适配器转为 [neutral, happy, angry, sad] | [angry, disgust, fear, happy, neutral, other, sad, surprised, unknown] |
| 人脸 | [angry, disgust, fear, happy, sad, surprise, neutral] | [anger, disgust, fear, happy, neutral, sad, surprise]；标准化 anger→angry、surprise→surprised |
| 姿态 | [ang, sad, neu, hap] | [ang, sad, neu, hap]；不变 |

音频现在覆盖愤怒、厌恶、恐惧、高兴、中性、其他、悲伤、惊讶、未知。人脸七类为愤怒、厌恶、恐惧、高兴、中性、悲伤、惊讶。姿态四类为愤怒、悲伤、中性、高兴。

特别注意人脸索引 4～6 已变化；旧模型的索引 4 是 sad，新模型索引 4 是 neutral。标签名称相近不代表索引顺序相同。

## 7. 辅助模型、结果汇总与融合

### 7.1 表格之外的辅助资源

| 辅助能力 | 当前资源 | 文件大小 | 作用 |
| --- | --- | --- | --- |
| 语音转写 | Dolphin base.cn.streaming；配置使用 CUDA | 主检查点约 426.46 MiB | 音频转文字，供问诊和文本分类使用 |
| 人脸定位 | OpenCV Haar frontal-face XML | 约 0.89 MiB | 找出人脸裁剪区域 |
| 人体定位 | MediaPipe pose_detection.tflite | 约 2.82 MiB | 检测人体 |
| 骨架提取 | MediaPipe pose_landmark_full.tflite，complexity=1 | 约 6.14 MiB | 提取骨架关键点 |

这些资源不计入四个情绪模型的 ONNX 大小，也不新增情绪模态。当前 ONNX Runtime 可用 provider 是 CPU；四个情绪模型的 GPU 执行由项目 TensorRT 适配层直接完成，不能仅根据 ORT provider 名称判断是否使用 GPU。

### 7.2 分数的不同含义

- 单次模型 score：在该模型预设类别中的相对概率，不等于真实正确率，也不等于抑郁诊断概率。
- 整轮视觉 primary_ratio：该标签出现次数 / 有效样本总数；例如十个有效姿态结果中六次悲伤，占比是 60%。
- 当前姿态看板优先显示整轮汇总 primary_score，却仍使用“置信度”文字，此时实际是主标签出现占比。
- no_face、no_pose 和 collecting 是采集/处理状态，不应作为有效情绪类别统计。

单次结果绑定会话、轮次、问题和时间；实时快照经接口/SSE 更新前端，轮次 bundle 汇总后保存并供下游消费。

### 7.3 下游规则使用

代码默认多模态内部基础权重为 EEG 20%、文本 20%、语音 20%、人脸 30%、姿态 10%；实际有效权重会受可用性、质量及置信度影响，规则配置可以覆盖默认值。默认综合评分将量表与多模态按 80% / 20% 组合。

新音频 angry 已兼容旧规则的 ang。默认语音负性集合包含悲伤与愤怒，新增 fear/disgust 未自动加入；识别类别和怎样参与风险评分是不同层次。上述为代码默认规则，不等同于读取并确认每个会话的实际生效规则。

## 8. 已验证范围与待核对事项

已有板端证据：四个模型加载、实际输入输出、CPU/GPU 数值对照、音频上传与转写链路，以及 2026-10-07 三十分钟四模态并发验收均通过。900 轮、3,600 次请求，错误、服务重启和 OOM 均为零。

| 模态 | 该次接口 P50 | 该次接口 P95 |
| --- | --- | --- |
| 文本 | 86.26 ms | 109.79 ms |
| 音频 | 91.49 ms | 115.10 ms |
| 人脸 | 110.36 ms | 135.50 ms |
| 姿态 | 118.10 ms | 140.25 ms |

这些是固定素材、每两秒一轮四模态并发条件下的接口耗时，包含相关前处理，不是纯模型耗时，不含完整浏览器录音等待及全链 ASR 延迟，也不能代表多用户生产性能或分类准确率。本次报告编写未重新运行三十分钟测试。

需要单独核对的姿态契约：随交付训练参考代码执行根节点居中、尺度归一化和 96 帧时间重采样；当前运行适配器直接将映射后的八至 96 帧送入模型，未执行相同预处理。差异在代码层面可确认，但是否完全对应 seed72 检查点的实际训练数据和预处理，仍需核对训练契约并用真实骨架样本验证。本报告没有据此擅自修改姿态链路。

还需在真实问诊素材中评估：中文转写误差对文本分类的传递、采样节奏与姿态训练时序的匹配、人脸裁剪质量、九类音频与下游负性规则的映射，以及各模型在目标场景中的准确率与置信度校准。运行验证和识别效果验证应分别记录。

## 9. 证据与交付文件

- [旧模型 ONNX 图与文件证据](old-model-graph-evidence.json)：真实旧权重中的结构名称、输入输出和 Git LFS 哈希。
- [机器可读新旧对照](comparison.json)：文件字节数、类别、张量契约、旧新版本和引擎大小。
- [浏览器可直接打开的完整报告](report.html)：两张流程图已内嵌，无需联网或安装 Mermaid。
- [原数据关系图](original-data-flow.svg) / [当前数据关系图](current-data-flow.svg)：可单独用于汇报材料。
- [本板四模态升级与验收](../../docs/operations/jetson-four-modal-upgrade-20261007.md)。
- [升级前模型检查记录](../../docs/operations/jetson-model-check-20261007.md)。
- [当前模型交付清单](../four_modal_onnx_upgrade_v1_20261003/model_manifest.json)。
- [姿态训练参考代码](../four_modal_onnx_upgrade_v1_20261003/reference/pose/agcn_model_and_dataset.py) / [当前姿态适配器](../../services/multimodal-service/runtime-assets/models/pose_emotion/infer_pose.py)。
- 模型作者资料：[emotion2vec_plus_large](https://huggingface.co/emotion2vec/emotion2vec_plus_large)、[ViT Facial Expression Recognition](https://huggingface.co/mo-thecreator/vit-Facial-Expression-Recognition)。当前大小和部署契约以本项目实物及代码为准。
