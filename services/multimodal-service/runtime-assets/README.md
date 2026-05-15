# Runtime Assets Layout

这个目录用于存放 `multimodal-service` 运行时真正依赖的模型与静态资产。

约定：

- 所有模型文件必须复制进当前仓库
- 不允许依赖旧项目 `D:\Projects\MCS\depression` 的运行时路径
- 不允许通过软链接、硬链接或绝对路径引用旧项目模型

建议目录：

- `asr/`
  - Dolphin ASR 模型，如 `small.pt`
- `audio-emotion/`
  - 语音情绪 ONNX、`labels.json`、`preprocessor/`
- `text-emotion/`
  - 文本情绪 ONNX、`labels.json`、`tokenizer/`
- `face-emotion/`
  - 表情识别 ONNX 及相关级联分类器
- `pose-emotion/`
  - 姿态识别 ONNX、`labels.json`
- `eeg/`
  - EEG FastAPI 对接所需配置、协议文件、示例 payload

后续实现时：

- Dockerfile 只从当前仓库复制这些资产
- 配置项只指向当前服务目录下的文件
