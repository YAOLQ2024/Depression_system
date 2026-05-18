# Non-EEG Four Modality Assets

这里存放当前直接并入 `multimodal-service` 的非 EEG 四模态模型资产与对应推理脚本。

当前包含：

- `text_emotion/`：文本情绪识别
- `audio_emotion/`：语音情绪识别
- `face_emotion/`：面部情绪识别
- `pose_emotion/`：姿态情绪识别

当前明确不包含：

- ASR 语音转写
- EEG 模态

命名约定：

- `app/models/non_eeg/` 作为非 EEG 模型根目录
- 子目录统一使用 `snake_case`
- 外部 API 路径可以继续保留业务语义化短横线命名，不和内部目录强绑定

迁移原则：

- 所有模型文件和推理脚本都来自既有交付版
- 不依赖旧项目绝对路径
- 后续 `multimodal-service` 内部只从这里读取非 EEG 四模态资产
