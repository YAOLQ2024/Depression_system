# `consultation` Step 4 详细设计：数字人问诊页主链与多模态接入

## 1. 文档目的

这份文档用于细化 `backend-integration-plan.md` 里原本偏高层的 Step 4。

原因很直接：

- 原先 Step 4 只覆盖了“问诊页接通 consultation 接口”
- 但你现在已经明确了数字人视频、语音转写、原始音频留存、四阶段真实进度、多模态持续运行、EEG 外部接入、各模型结果持久化这些要求
- 这已经不是“接一下问诊页”这么简单，而是一次完整的页面主链设计

所以这份文档作为 Step 4 的详细主文档使用。

## 2. 这次要解决的核心问题

V1 数字人问诊阶段要同时满足：

1. 页面中间播放数字人视频，一个问题对应一个视频
2. 用户以语音回答为主，后端自动做语音转写
3. 数字人问题文本、视频元数据、用户原始语音、转写文本都要入库，但视频文件本体不进关系数据库
4. 多模态模型在问诊过程中持续运行：
   - EEG
   - 表情识别
   - 姿态情绪识别
   - 语音情绪识别
   - 文本情绪识别
5. 各模态结果都要和“当前问诊会话 / 当前问题 / 当前回答窗口”绑定
6. 页面顶部进度条必须是真实阶段进度，不再是假 UI
7. 阶段四完成后，用户再手动进入量表问诊

## 3. V1 明确结论

### 3.1 问诊流程采用固定视频序列，不做自动追问

V1 明确采用：

- 固定视频顺序
- 固定问题顺序
- 不做自动追问
- 不做 LLM 生成问题
- 不做规则分支追问

这和当前 `consultation-service` 中已有的 `route_by_rule / decision / speak_then_wait` 规则链并不完全一致。

因此 Step 4 不是单纯“把现有规则引擎接到前端”，而是要在保留 4 个主阶段的前提下，把 V1 的问诊执行方式收口为：

- `固定 stage`
- `固定 prompt playlist`
- `固定视频资产`
- `固定回答窗口`

### 3.2 四个阶段保持不变，但阶段内部改为真实视频播放流

V1 仍然保留老师确认的 4 个阶段：

1. `问候说明`
2. `主诉采集`
3. `现病史`
4. `风险筛查`

但页面层和服务层的执行方式改成：

- 阶段一：播放 1 个问候说明视频，播放完自动进入阶段二，不等待用户回答
- 阶段二：按固定顺序播放 2-4 个主诉问题视频，每播完一个视频就等待用户语音回答
- 阶段三：按固定顺序播放现病史视频，每播完一个视频就等待用户语音回答
- 阶段四：按固定顺序播放风险筛查视频，每播完一个视频就等待用户语音回答
- 阶段四结束后，不自动跳量表，由用户点击按钮进入下一流程

### 3.3 浏览器仍然只能访问网关

保持系统总原则：

- 浏览器只访问 `gateway-service`
- 不直接请求 `consultation-service`
- 不直接请求 `multimodal-service`
- 不直接请求 EEG 采集源

网关后面再按职责转发：

- 问诊主链 -> `consultation-service`
- 多模态采集 / 推理 / 汇总 -> `multimodal-service`
- EEG 采集适配 -> 由 `multimodal-service` 内部通过 provider 适配层统一接入

### 3.4 EEG 统一走 `multimodal-service -> Windows EEG FastAPI`

你现在在 Windows 本机开发，并且本机具备蓝牙能力，但仍然不建议让前端直接碰 EEG 设备。

更稳的做法是：

- 仍然保持 `browser -> gateway -> multimodal-service` 这条边界不变
- `multimodal-service` 统一转调 Windows EEG FastAPI 服务

原因：

- 你后续最终还是要部署回 Linux 主机
- 现在就统一成同一条链路，后面迁移环境时不用再改协议
- 本机 Windows 开发时，也可以直接在本机起 Windows EEG FastAPI，仍然符合这条链路

因此结论是：

- 不做两套 EEG 方案
- 不做浏览器直连 EEG
- 不做 `multimodal-service` 直接本地蓝牙适配
- 统一保持：`browser -> gateway -> multimodal-service -> Windows EEG FastAPI`

### 3.5 这里的 `prompt` 不是 LLM prompt，而是“固定问题项 key”

你这个提醒很重要。

在 Step 4 里写 `prompt`，不是指“给大模型喂的提示词”，而是沿用当前 `consultation-service` 里的命名习惯，表示：

- 当前这一题的问题项
- 当前这一段数字人播报项
- 当前 turn 对应的固定脚本节点

为了避免误解，后续文档和前端展示层推荐优先使用：

- `question_item`
- `question_key`
- `question_text`

但在服务端和数据库层，可以暂时保留 `prompt_key` 这个内部稳定字段名，原因是：

- 它已经和现有 `consultation-service` 术语比较接近
- 改动成本比重新发明一套字段更低
- 我们只需要明确：它不是 LLM prompt，而是“固定问题项的唯一 key”

## 4. 页面交互设计

## 4.1 页面中心区

页面中间不再是假发光圆环，而是：

- 一个真实视频播放器
- 当前问题字幕区
- 用户回答转写字幕区
- 一个很小的当前状态提示区

建议状态机：

- `warming_up`
- `playing_prompt`
- `waiting_user_response`
- `recording_response`
- `processing_response`
- `ready_for_next_prompt`
- `completed_waiting_assessment_entry`
- `paused_for_human_review`

## 4.2 顶部真实进度条

顶部进度条不能再由前端 mock 的 step number 驱动，而应由后端返回：

- `current_stage_id`
- `current_stage_label`
- `stage_index`
- `total_stages`

展示语义建议：

- 只展示四个主阶段
- 不展示“当前阶段内部第几题”
- 当前阶段通过高亮或连线进度表达即可

原因：

- 老师要求界面简洁
- 页面中间的视频区优先级更高
- 阶段内部题目数量后续可能调整，不需要提前暴露给用户

## 4.3 字幕区

字幕区建议拆成两块：

- `数字人提问字幕`
- `用户回答转写字幕`

不要只显示一份混合文本，否则后面回放和调试很难看。

建议每次回答完成后，当前字幕区保留：

- 本题问题文本
- 本题最终转写文本

## 4.4 多模态数据看板

右侧数据看板必须显示真实状态，而不是随机数或假动画。

但界面必须尽量克制，V1 建议收口为：

- 一个摄像头框
- 一个 EEG 可视化图
- 当前语音情绪
- 当前文本情绪
- 当前表情主情绪
- 当前姿态主情绪
- EEG 当前分类标签

这里的“当前”指：

- 当前会话最近一次成功推理结果
- 或当前回答窗口内的最新聚合状态

不在 UI 中显示：

- 模型预热状态
- 看板顶部说明文字
- 最近一次更新时间
- EEG 当前置信度

## 5. 资产与配置设计

## 5.1 视频资产不进数据库

数字人问题视频属于：

- 固定资产
- 版本化内容
- 非用户数据

因此不建议把视频二进制放进数据库。

建议方式：

- 视频文件放对象存储或静态资源目录
- 数据库只保存 `video_asset_id / video_uri / manifest_version`

推荐：

- 开发环境可先放 `consultation/client/public/digital-human/`
- 稳定后迁到 MinIO，并由配置返回可访问 URI

说明：

- MinIO 更准确地说是对象存储，不是关系数据库
- 这类视频文件更适合放对象存储或静态目录，不适合放 PostgreSQL 这类关系库
- 因此“视频文件不入数据库，数据库只记元数据”仍然是最合适的方案

## 5.4 模型资产迁入规则

后续真正写代码时，所有需要的模型文件都必须从旧项目复制到新项目中，不能运行时链接旧项目路径。

原因：

- 旧项目 `D:\Projects\MCS\depression` 后续会被删除
- 运行时依赖旧项目路径会让新系统不可迁移、不可部署
- Docker 构建也不能依赖仓库外的历史目录

规则：

- 只允许“复制进新项目”
- 不允许通过软链接、硬链接、绝对路径引用旧项目模型
- 不允许在新服务里直接 import 旧项目代码作为长期方案

推荐落点：

- `services/multimodal-service/runtime-assets/asr/`
- `services/multimodal-service/runtime-assets/audio-emotion/`
- `services/multimodal-service/runtime-assets/text-emotion/`
- `services/multimodal-service/runtime-assets/face-emotion/`
- `services/multimodal-service/runtime-assets/pose-emotion/`
- `services/multimodal-service/runtime-assets/eeg/`

## 5.2 增加固定视频清单 manifest

当前 `workflow-resources` 已有四个阶段脚本，但它们更偏“文本问答规则”。

为了满足“一个问题一个视频，顺序固定不变”的要求，建议新增一份 manifest，例如：

- `packages/workflow-resources/digital-human-playlists/consultation-v1.yaml`

当前可以先创建占位文件，等你明天给出最终视频清单和字幕文本后再补全。

manifest 的业务语义建议优先使用：

- `question_items`
- `question_key`
- `question_text`

这样更容易和“固定问题项”语义对齐，不会和 LLM prompt 混淆。

建议字段：

```yaml
workflow_id: consultation-v1
manifest_contract: digital-human-playlist/v1
playlist_version: video-playlist-v1
stages:
  - stage_id: stage-01-greeting-and-briefing
    stage_order: 1
    question_items:
      - question_key: greeting-001
        order: 1
        node_id: greeting-open
        video_asset_id: greeting-001
        video_uri: /digital-human/consultation-v1/001.mp4
        question_text: 您好，我是本次陪您完成问诊的数字医生...
        subtitle_text: null
        response_required: false
  - stage_id: stage-02-chief-complaint
    stage_order: 2
    question_items:
      - question_key: chief-complaint-001
        order: 1
        node_id: ask-chief-complaint
        video_asset_id: chief-complaint-001
        video_uri: /digital-human/consultation-v1/002.mp4
        question_text: 现在请您放轻松，先和我说说...
        subtitle_text: null
        response_required: true
```

核心原则：

- `stage_id` 与现有 workflow 保持一致
- `stage_order` 明确四阶段固定顺序
- `node_id` 保持可追踪
- 顺序由 `order` 明确控制
- `question_text` 是后续和用户语音、转写文本一一绑定入库的权威问题文本
- `subtitle_text` 只是展示层覆盖字段，缺省时可直接回退为 `question_text`
- V1 不做分支跳转，只做线性顺序
- `consultation-service` 读取后，可在内部把 `question_key` 映射成现有更接近实现的 `prompt_key`

## 5.3 旧版模型资产格式结论

从旧版 `D:\Projects\MCS\depression` 中可以明确看出，后续模型资产格式可以直接按下面收口：

### 语音转写 ASR

旧版参考：

- `models/dolphin/small.pt`
- `my_flask_app/utils/speech_recognition_dolphin.py`

结论：

- ASR 不是 ONNX，而是 Dolphin 模型加载方式
- 当前看到的是 `.pt` 权重文件
- 需要 `dolphin` Python 运行时

### 文本情绪识别

旧版参考：

- `services/multimodal_service/text/model.onnx`
- `services/multimodal_service/text/labels.json`
- `services/multimodal_service/text/tokenizer/*`

结论：

- 模型主体：`model.onnx`
- 标签映射：`labels.json`
- tokenizer 目录必须保留

### 语音情绪识别

旧版参考：

- `services/multimodal_service/audio/model.onnx`
- `services/multimodal_service/audio/labels.json`
- `services/multimodal_service/audio/preprocessor/preprocessor_config.json`

结论：

- 模型主体：`model.onnx`
- 标签映射：`labels.json`
- 预处理器目录必须保留

### 表情识别

旧版参考：

- `services/multimodal_service/face/model.onnx`
- `services/multimodal_service/face/infer_face.py`

结论：

- 模型主体：`model.onnx`
- 标签映射内置在代码里
- 预处理依赖 OpenCV + Haar Cascade

### 姿态情绪识别

旧版参考：

- `services/multimodal_service/pose/model.onnx`
- `services/multimodal_service/pose/labels.json`
- `services/multimodal_service/pose/infer_pose.py`

结论：

- 模型主体：`model.onnx`
- 标签映射：`labels.json`
- 前处理依赖 MediaPipe Pose
- 推理是“图像帧 -> MediaPipe 33 点 -> shared21 -> ONNX”

### EEG

旧版参考：

- `docs/eeg_api_unified_design_v1_20260412.md`
- `my_flask_app/utils/multimodal/eeg/api_client.py`

结论：

- EEG 不是本地模型文件直接推理
- EEG 当前推荐架构是“Windows EEG FastAPI 提供采集与分类能力，`multimodal-service` 统一转调”
- 新系统里应把 EEG 视为 `multimodal-service` 背后的能力源，而不是直接嵌进浏览器

## 6. 服务职责边界

## 6.1 `consultation-service`

负责：

- 问诊会话创建
- 当前 prompt 顺序推进
- 四阶段真实进度
- turn 完成判定
- 问题文本与视频元数据回传
- 阶段四完成后生成量表入口状态

不负责：

- 模型推理
- 原始音频文件存储
- 表情 / 姿态 / EEG 结果落库细节

## 6.2 `multimodal-service`

负责：

- 模型预热
- 语音转写
- 语音情绪识别
- 文本情绪识别
- 表情识别
- 姿态识别
- Windows EEG FastAPI 转调
- 原始音频对象存储
- 原始 EEG 片段压缩后对象存储
- 多模态结果持久化
- turn 级别多模态汇总
- session 级别多模态汇总

不负责：

- 决定问下一个什么问题
- 决定是否进入量表
- 最终临床风险结论

## 6.3 Windows EEG FastAPI 转调层

推荐职责：

- 统一封装 EEG FastAPI 的调用方式
- 输出统一的 `channels / classification / latest / history / health / meta`

在新系统中的调用位置：

- 由 `multimodal-service` 内部调用
- 浏览器不直接连 Windows EEG FastAPI

推荐实现：

- Windows 开发机上可本机启动 EEG FastAPI
- Linux 部署时继续转调 Windows EEG FastAPI
- 前后端契约不因部署环境变化而变化

## 7. 建议的主链调用流程

## 7.1 开始问诊

1. 前端调用 `POST /api/v1/consultations`
2. 前端调用 `POST /api/v1/consultations/{session_id}/start`
3. `consultation-service` 创建或绑定一个 `multimodal_session`
4. `consultation-service` 异步通知 `multimodal-service` 预热模型
5. 前端进入问诊页，拿到：
   - 当前阶段
   - 当前 prompt
   - 当前视频地址
   - 多模态会话状态

## 7.2 阶段一：问候说明

1. 前端自动播放 greeting 视频
2. greeting 播放时，后端异步预热：
   - ASR
   - 语音情绪
   - 文本情绪
   - face
   - pose
   - EEG FastAPI 健康检查
3. 视频播完后，前端调用一个“系统 prompt 完成”接口
4. 后端推进到阶段二

建议新增：

- `POST /api/v1/consultations/{session_id}/question-items/{prompt_key}/complete`

它只用于：

- `response_required = false` 的系统视频

## 7.3 阶段二到阶段四：一个视频 -> 一个回答 -> 下一个视频

每个问题的标准流程：

1. 前端播放当前 question item 视频
2. 视频播放结束后，页面切到等待回答态
3. 用户开始语音回答
4. 浏览器本地录音
5. 浏览器在回答窗口中持续采集：
   - face 图像帧
   - pose 图像帧
6. `multimodal-service` 持续拉取或接收 EEG 当前窗口数据
7. 用户结束回答
8. 浏览器把整段音频提交到后端
9. 后端做：
   - 原始音频存对象存储
   - ASR 转写
   - 语音情绪识别
   - 文本情绪识别
   - 汇总回答窗口内的 face/pose/eeg 结果
10. `consultation-service` 写入这一题 turn，并推进到下一个 question item

## 8. 接口建议

下面是建议新增或细化的接口，不要求这一步一次性全做完，但契约应该先统一。

## 8.1 面向浏览器的网关接口

### 问诊主链

- `POST /api/v1/consultations`
- `GET /api/v1/consultations/{session_id}`
- `POST /api/v1/consultations/{session_id}/start`
- `POST /api/v1/consultations/{session_id}/question-items/{prompt_key}/complete`
- `POST /api/v1/consultations/{session_id}/turns/audio-answer`
- `POST /api/v1/consultations/{session_id}/manual-input`
- `POST /api/v1/consultations/{session_id}/complete`

### 多模态采集

- `POST /api/v1/consultations/{session_id}/captures/face`
- `POST /api/v1/consultations/{session_id}/captures/pose`
- `GET /api/v1/consultations/{session_id}/multimodal/live`
- `GET /api/v1/consultations/{session_id}/multimodal/turns/{turn_id}/bundle`

### EEG 展示

不建议前端单独访问 EEG 路径，而是由：

- `GET /api/v1/consultations/{session_id}/multimodal/live`

统一返回 EEG 最新状态。

## 8.2 `consultation-service` 内部建议

建议继续保持 `consultations` 为主入口，但扩展返回结构。

`GET /consultations/{session_id}` 建议返回新增字段：

- `current_prompt_key`
- `current_prompt_order`
- `current_prompt_video_asset_id`
- `current_prompt_video_uri`
- `current_prompt_question_text`
- `current_prompt_subtitle_text`
- `total_prompt_count`
- `completed_prompt_count`
- `current_stage`
- `current_question_item`

说明：

- 这里保留 `current_prompt_*` 命名只是为了兼容现有服务内部语义
- 对外产品语义可以解释为“当前问题项 / 当前视频项”
- `response_required` 继续从 `current_question_item.response_required` 读取
- `multimodal_session_id` 属于后续多模态接线步骤，不在 `4A-3` 首批落地范围内

## 8.3 `multimodal-service` 内部建议

建议新增：

- `POST /api/v1/multimodal/sessions`
- `POST /api/v1/multimodal/sessions/{session_id}/warmup`
- `POST /api/v1/multimodal/sessions/{session_id}/audio-turns`
- `POST /api/v1/multimodal/sessions/{session_id}/captures/face`
- `POST /api/v1/multimodal/sessions/{session_id}/captures/pose`
- `GET /api/v1/multimodal/sessions/{session_id}/live`
- `GET /api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle`

其中：

- `audio-turns` 负责整段回答音频的存储与异步/同步推理
- `captures/face` / `captures/pose` 负责提交抽样帧
- `live` 负责返回当前看板状态

## 9. 数据库与对象存储设计

## 9.1 `consultation-service` 表演进建议

当前已有：

- `consultation_sessions`
- `consultation_turns`

建议扩展。这里区分为：

- `4A-3` 首批必须落地，用于固定视频问诊主链和问答绑定入库
- 后续多模态步骤再继续补充 EEG / face / pose / audio capture 关联字段

### consultation_sessions 增加

- `playlist_version`
- `current_prompt_key`
- `current_prompt_order`
- `current_prompt_video_asset_id`
- `current_prompt_video_uri`
- `current_prompt_question_text`
- `current_prompt_subtitle_text`
- `total_prompt_count`
- `completed_prompt_count`

后续步骤再增加：

- `multimodal_session_id`
- `delivery_mode`

### consultation_turns 增加

- `turn_index`
- `prompt_key`
- `prompt_order`
- `prompt_video_asset_id`
- `prompt_video_uri`
- `prompt_question_text`
- `prompt_subtitle_text`
- `response_started_at`
- `response_completed_at`

后续步骤再增加：

- `response_audio_capture_id`
- `multimodal_bundle_id`

这样一条 `consultation_turn` 就能明确回答：

- 这是第几题
- 播的是哪个视频
- 对应哪段回答音频
- 对应哪份多模态汇总

## 9.2 `multimodal-service` 建议新增表

### multimodal_sessions

- `id`
- `owner_service`
- `owner_session_id`
- `user_id`
- `status`
- `warmup_status`
- `started_at`
- `updated_at`

### multimodal_session_summaries

- `id`
- `session_id`
- `modality`
- `summary_scope`
- `primary_label`
- `primary_score`
- `top_labels`
- `result_payload`
- `window_started_at`
- `window_ended_at`
- `generated_at`

### multimodal_captures

- `id`
- `session_id`
- `consultation_turn_id`
- `modality`
- `capture_kind`
- `segment_index`
- `source_uri`
- `file_format`
- `sampling_rate`
- `capture_started_at`
- `capture_ended_at`
- `processing_status`
- `quality_flags`

### multimodal_inference_results

- `id`
- `session_id`
- `consultation_turn_id`
- `capture_id`
- `modality`
- `model_name`
- `model_version`
- `label`
- `score`
- `result_payload`
- `window_started_at`
- `window_ended_at`
- `created_at`

### multimodal_turn_bundles

- `id`
- `session_id`
- `consultation_turn_id`
- `transcript_text`
- `speech_emotion_summary`
- `text_emotion_summary`
- `face_summary`
- `pose_summary`
- `eeg_summary`
- `quality_flags`
- `generated_at`

## 9.3 什么进数据库，什么进对象存储

### 必须进对象存储

- 用户原始回答音频
- 原始 EEG 片段，按时间窗压缩后入对象存储
- 可选：调试留样的 face/pose 关键帧

### 必须进数据库

- 视频问题元数据
- 用户转写文本
- 各模态推理结果
- 各 turn 的时间窗口
- 原始音频对象存储 URI
- 原始 EEG 片段对象存储 URI
- EEG 分类结果
- turn 级别聚合结果
- session 级别聚合结果

### 不建议直接塞进关系数据库的大对象

- 完整原始音频二进制
- 完整视频帧流
- 长时间原始 EEG 波形

## 10. 多模态结果如何和问题绑定

这是这一步最关键的约束之一。

原则：

- 所有模态结果都必须至少同时带：
  - `consultation_session_id`
  - `consultation_turn_id`
  - `prompt_key`
  - `window_started_at`
  - `window_ended_at`

这样才能保证：

- 问题和回答一一对应
- 原始音频不会串到别的问题
- face/pose/eeg 的结果能回看属于哪一次回答窗口

其中：

- 原始音频：严格按 turn 绑定
- ASR 转写：严格按 turn 绑定
- 语音情绪：严格按 turn 绑定
- 文本情绪：严格按 turn 绑定
- face/pose：同时保留 session 连续时间流和 turn 级回答窗口汇总
- EEG：同时保留 session 连续时间流和 turn 级回答窗口汇总

额外建议：

- `question_text + prompt_key + turn_index` 作为问答绑定真源
- `video_uri` 只是播放资源引用，不作为业务主键

## 11. 模型调用策略

## 11.1 语音转写与语音情绪分离

这两件事必须是两条独立能力：

- ASR：把语音转成文字
- Speech Emotion：从语音信号本身识别情绪

即便它们都消费同一段原始音频，也不能混成一个字段。

建议：

- 同一段音频上传一次
- `multimodal-service` 内部分别调用：
  - Dolphin ASR
  - Audio Emotion ONNX

## 11.2 文本情绪识别在 ASR 之后执行

流程应为：

1. 先完成 ASR
2. 拿到 transcript
3. 再调用 Text Emotion ONNX

也就是说：

- 文本情绪不是基于 prompt 文本
- 而是基于用户回答的转写文本

## 11.3 face / pose 持续运行，保存“连续时间流 + turn 汇总 + session 汇总”三层结果

推荐采样节奏参考旧版：

- face：约 `1.5s` 一帧
- pose：约 `1.0s` 一帧

你现在提出的想法本质上是：

- 从摄像头打开开始，到阶段四结束为止连续采样
- 每一帧都有自己的标签
- 最后按出现次数统计 top 1 或 top 3，作为整个数字人问诊阶段的表情情绪 / 姿态情绪结果

这个设计是合理的，但建议不要只保留“全程最后一个总结果”，而是拆成三层：

1. 连续时间流
   - 每次采样都有时间戳、标签、分数
   - 落 `multimodal_inference_results`
2. turn 级汇总
   - 只统计某一道问题回答窗口内出现最多的 top 1 / top 3
   - 用于和当前问题绑定
3. session 级汇总
   - 从摄像头开启到阶段四结束，统计整个问诊期间出现最多的 top 1 / top 3
   - 用于老师后续看总体状态

建议：

- 细粒度结果落 `multimodal_inference_results`
- 每个 turn 完成时生成 `face_summary / pose_summary`
- 阶段四结束时再生成 `session_summary`
- summary 至少包含：
  - 主标签
  - 主置信度
  - top 3 labels
  - 各标签占比
  - no_face / no_pose 比例
  - 质量标记

## 11.4 EEG 持续运行，保存“原始片段 + 连续结果 + turn 汇总 + session 汇总”

推荐：

- EEG 通道波形和分类由 Windows EEG FastAPI 持续提供
- `multimodal-service` 维护时间序列缓存
- 原始 EEG 片段按固定时间窗压缩后写入对象存储
- 推理结果按时间窗落 `multimodal_inference_results`
- 当某个回答 turn 完成时，按 `response_started_at ~ response_completed_at` 截取这一窗口生成 turn 汇总
- 阶段四结束后，按整段问诊窗口再生成 session 汇总

建议保存：

- 原始 EEG 压缩片段对象存储 URI
- 时间窗标签与置信度
- turn 级 EEG top 1 / top 3
- session 级 EEG top 1 / top 3
- 数据质量标记

不建议把整段超长原始 EEG 波形直接塞进关系数据库。

## 11.5 语音情绪识别保存策略

语音情绪最适合按“每一道问题的一次回答”保存。

原因：

- 一道题通常对应一段连续录音
- 它天然和 `consultation_turn` 一一对应

建议每个 turn 保存：

- `primary_label`
- `primary_score`
- `top_3_labels`
- `full_scores_json`
- `audio_duration_ms`
- `model_name`
- `model_version`

如果后面老师希望看整段问诊的总体语音情绪趋势，再额外基于 turn 结果做 session 汇总即可。

## 11.6 文本情绪识别保存策略

文本情绪也最适合按 turn 保存。

流程：

1. 用户回答音频上传
2. ASR 产出 transcript
3. 用 transcript 调文本情绪模型
4. 结果绑定当前 `consultation_turn`

建议每个 turn 保存：

- `transcript_text`
- `text_emotion_primary_label`
- `text_emotion_primary_score`
- `text_emotion_top_3_labels`
- `text_emotion_full_scores_json`

如果后续需要整段问诊的文本情绪总体标签，再按各 turn 结果做 session 汇总。

## 12. 模型预热与运行时

## 12.1 预热时机

预热时机放在：

- 问诊开始后
- 阶段一问候说明视频播放期间

这样可以尽量把模型加载延时藏到 greeting 阶段中。

## 12.2 预热对象

建议预热：

- Dolphin ASR
- 文本情绪 ONNX
- 语音情绪 ONNX
- Face ONNX
- Pose ONNX

EEG 不是“预热模型”，而是：

- 做远程服务健康检查
- 检查通道是否可读
- 检查最新分类接口是否可用

## 12.3 运行状态返回

前端看板接口可以继续保留完整运行状态，但 UI 默认只显示最必要信息：

- 摄像头画面
- 当前语音情绪
- 当前文本情绪
- 当前表情主情绪
- 当前姿态主情绪
- EEG 当前分类标签
- EEG 可视化图数据

`warming / ready / error` 这类模型运行细节可以保留在接口里，但默认不显示在主页面上。

## 13. 对当前 workflow 资源的处理建议

当前资源里：

- `stage-01-greeting-and-briefing.yaml`
- `stage-02-chief-complaint.yaml`
- `stage-03-current-history-followup.yaml`
- `stage-04-high-risk-screening.yaml`

仍然很有价值，但它们当前更偏：

- 文本 prompt
- extraction 规则
- 风险筛查逻辑

要满足你现在的视频固定顺序要求，建议：

1. 保留这些文件作为“阶段语义真源”
2. 新增 `video-playlist manifest` 作为“播放顺序真源”
3. V1 暂时不走 `route_by_rule` 动态分支
4. 风险筛查的结构化结果仍然沿用当前 `consultation-service` 的 slot / summary 思路

特别注意：

- 当前 `stage-01-greeting-and-briefing.yaml` 里是“问候后等待用户说开始”
- 这和你现在要求的“问候视频播完自动进入下一阶段”不一致

因此 Step 4 实施时需要同步改这一阶段脚本语义。

## 14. 建议的分步实施顺序

Step 4 不建议一把做完。

原来的 `4A ~ 4F` 可以保留为一级阶段，但真正开发时建议按下面的二级子步骤推进。这样每一步都能单独验证，也更容易定位错误。

### Step 4A：先改会话语义与固定视频清单

#### Step 4A-1：确定固定视频清单 manifest 契约

目标：

- 固定 `digital-human-playlists/consultation-v1.yaml` 的字段结构
- 明确 top-level / stage / question item 三层字段边界
- 明确每个问题项都必须有：
  - `question_key`
  - `order`
  - `video_asset_id`
  - `video_uri`
  - `question_text`
  - `subtitle_text`
  - `response_required`
- 明确每个 stage 都必须有：
  - `stage_id`
  - `stage_order`

完成标志：

- manifest 占位文件存在
- `digital-human-playlists/README.md` 明确字段含义和边界
- 后续只需要补视频资产和文本，不再改字段结构

#### Step 4A-2：让 `consultation-service` 能读取 manifest

目标：

- 服务能从 workflow 资源中加载固定视频清单
- 会话启动时能确定：
  - 当前阶段
  - 当前问题项
  - 当前视频地址
  - 是否需要回答

完成标志：

- `POST /consultations/{id}/start` 后，服务端有当前问题项状态

#### Step 4A-3：扩展 `consultation_sessions` / `consultation_turns` 字段

目标：

- 为固定视频问诊补齐数据库字段
- 首批落库字段至少包括：
  - `playlist_version`
  - `current_prompt_key`
  - `current_prompt_order`
  - `current_prompt_video_asset_id`
  - `current_prompt_video_uri`
  - `current_prompt_question_text`
  - `current_prompt_subtitle_text`
  - `total_prompt_count`
  - `completed_prompt_count`
  - `turn_index`
  - `prompt_key`
  - `prompt_order`
  - `prompt_video_asset_id`
  - `prompt_video_uri`
  - `prompt_question_text`
  - `prompt_subtitle_text`
  - `response_started_at`
  - `response_completed_at`

完成标志：

- 数据模型和迁移完成
- 新会话和 turn 能落这些新字段
- 暂不引入多模态关联字段，留给 `4D` / `4E`

#### Step 4A-4：改 greeting 阶段语义

目标：

- 把当前“问候后等待用户说开始”改成“问候视频播完自动进入下一阶段”

完成标志：

- 阶段一不再等待用户输入
- 后端支持系统问题项自动完成

### Step 4B：问诊页切到真实视频播放与真实四阶段进度

#### Step 4B-1：中间主区域切到真实视频播放器

目标：

- 用真实视频播放器替换当前假数字人主视觉
- 页面能显示：
  - 当前视频
  - 当前问题字幕
  - 用户回答字幕区
  - 很小的状态提示区

完成标志：

- 问诊页进入后可播放 manifest 中的真实视频

#### Step 4B-2：顶部只显示四阶段真实进度

目标：

- 顶部进度条改为后端驱动
- 只显示：
  - `问候说明`
  - `主诉采集`
  - `现病史`
  - `风险筛查`

完成标志：

- 当前阶段高亮由真实会话状态驱动
- 不再显示假步骤或题内进度

#### Step 4B-3：实现 greeting 自动推进

目标：

- 阶段一视频播放结束后，前端自动调用“系统问题项完成”接口
- 页面自动切到阶段二第一题

完成标志：

- 用户不需要任何点击，就能从问候说明进入主诉采集

### Step 4C：接通语音回答主链

#### Step 4C-1：浏览器录音和回答窗口控制

目标：

- 视频播完后进入等待回答态
- 用户可以开始录音、结束录音
- 回答窗口起止时间准确记录

完成标志：

- 前端能稳定拿到一段完整回答音频

#### Step 4C-2：原始音频上传与对象存储落地

目标：

- 把每道题的一段原始音频上传到后端
- `multimodal-service` 把音频写入对象存储
- 音频 URI 回写数据库

完成标志：

- 每个 `consultation_turn` 都能关联一段原始音频 URI

#### Step 4C-3：ASR 转写与 turn 落库

目标：

- 上传音频后调用 Dolphin ASR
- 保存最终 transcript
- 把“问题文本 + 用户音频 + transcript”一一绑定到同一个 turn

完成标志：

- 每道题都能在数据库中看到：
  - `question_text`
  - `audio_uri`
  - `transcript_text`

#### Step 4C-4：问诊问题项推进

目标：

- 一道题处理完成后自动推进到下一道题
- 阶段内题目播完后自动进入下一阶段

完成标志：

- 阶段二到阶段四都能按固定顺序完整走通

### Step 4D：接通语音情绪、文本情绪、face、pose

#### Step 4D-1：语音情绪识别落库

目标：

- 对每段回答音频跑语音情绪模型
- 结果按 turn 保存

完成标志：

- 每个 turn 至少有：
  - `primary_label`
  - `primary_score`
  - `top_3_labels`

#### Step 4D-2：文本情绪识别落库

目标：

- 用 ASR transcript 调文本情绪模型
- 结果按 turn 保存

完成标志：

- 每个 turn 至少有：
  - `text_emotion_primary_label`
  - `text_emotion_primary_score`
  - `text_emotion_top_3_labels`

#### Step 4D-3：face 连续采样与细粒度结果保存

目标：

- 从摄像头开启起按约 `1.5s` 抽样
- 每一帧表情识别结果带时间戳入库

完成标志：

- `multimodal_inference_results` 中可看到 face 时间流数据

#### Step 4D-4：pose 连续采样与细粒度结果保存

目标：

- 从摄像头开启起按约 `1.0s` 抽样
- 每一帧姿态情绪结果带时间戳入库

完成标志：

- `multimodal_inference_results` 中可看到 pose 时间流数据

#### Step 4D-5：生成 turn 级 face / pose 汇总

目标：

- 每道题回答完成后，按回答窗口统计当前题的 face / pose top 1 和 top 3

完成标志：

- 每个 turn 都有：
  - `face_summary`
  - `pose_summary`

#### Step 4D-6：生成 session 级 face / pose 汇总

目标：

- 从进入问诊页到阶段四结束，对整个问诊阶段生成一次总体汇总

完成标志：

- 会话结束后能得到 session 级 face / pose top 1 和 top 3

### Step 4E：接通 EEG 与真实多模态看板

#### Step 4E-1：`multimodal-service` 转调 Windows EEG FastAPI

目标：

- 打通 EEG FastAPI 健康检查、最新分类、历史数据获取

完成标志：

- `multimodal-service` 能稳定读到 EEG 数据

#### Step 4E-2：保存原始 EEG 压缩片段

目标：

- 按固定时间窗切片 EEG 原始数据
- 压缩后写入对象存储
- 保存片段 URI

完成标志：

- 数据库能关联 EEG 原始片段对象存储 URI

#### Step 4E-3：保存 EEG 细粒度时间流结果

目标：

- 把 EEG 分类时间流结果入库

完成标志：

- `multimodal_inference_results` 中可看到 EEG 时间流标签

#### Step 4E-4：生成 turn 级 EEG 汇总

目标：

- 按每道题的回答窗口汇总 EEG top 1 和 top 3

完成标志：

- 每个 turn 都有关联的 EEG 摘要结果

#### Step 4E-5：生成 session 级 EEG 汇总

目标：

- 对整个问诊阶段生成一次总体 EEG 汇总

完成标志：

- 会话结束后能得到 session 级 EEG top 1 和 top 3

#### Step 4E-6：看板接入真实摄像头框和 EEG 图

目标：

- 前端右侧看板接入：
  - 真实摄像头框
  - EEG 可视化图
  - 当前语音情绪
  - 当前文本情绪
  - 当前表情主情绪
  - 当前姿态主情绪
  - EEG 当前分类标签

完成标志：

- 看板不再是随机假数据
- 主页面不显示模型预热状态和 EEG 置信度

### Step 4F：阶段结束与量表入口

#### Step 4F-1：阶段四结束判定

目标：

- 风险筛查最后一个问题项完成后，问诊会话进入 `handoff_ready`

完成标志：

- 后端能稳定给出“已可进入量表”的状态

#### Step 4F-2：前端显示“进入量表问诊”入口

目标：

- 问诊页在完成后显示明确 CTA
- 用户手动点击进入下一流程

完成标志：

- 页面不会自动硬跳转
- 用户可清晰看到下一步入口

#### Step 4F-3：和 Step 5 量表问诊做交接

目标：

- 点击 CTA 后创建或恢复 assessment session
- 平滑进入量表页面

完成标志：

- 数字人问诊到量表问诊的 handoff 路径完整可用

## 15. 这一步明确不做的事

V1 Step 4 先不做：

- 自动追问
- LLM 动态提问
- 数字医生风格自由切换
- 浏览器直连 EEG Windows 服务
- 原始 face/pose 全帧永久存储
- 最终风险结论计算

## 16. 当前建议结论

你这次补充后的 Step 4，实质上已经从“接个问诊页”升级成：

- `consultation-service` 的问诊执行方式调整
- `multimodal-service` 的正式落库设计
- EEG 远程适配接入
- 问诊页真实视频化与真实进度化

原先总文档里的 Step 4 确实偏浅，不能直接覆盖这些需求。

这份文档后续应作为：

- Step 4 的详细设计主文档
- 后面拆接口、拆表、拆前端页面实现时的唯一细化依据
