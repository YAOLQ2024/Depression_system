# Non-EEG Four Modality Assets

这里是 `multimodal-service` 在开发环境下的非 EEG 四模态唯一模型根目录。

当前包含：

- `text_emotion/`：文本情绪识别
- `audio_emotion/`：语音情绪识别
- `face_emotion/`：面部情绪识别
- `pose_emotion/`：姿态情绪识别

当前明确不包含：

- ASR 语音转写
- EEG 模态

命名约定：

- `runtime-assets/models/` 作为非 EEG 模型根目录
- 子目录统一使用 `snake_case`
- 外部 API 路径可以继续保留业务语义化短横线命名，不和内部目录强绑定

运行约定：

- Compose 将宿主机 `runtime-assets/` 挂载到容器 `/app/runtime-assets`
- 服务运行时直接从这里读取脚本、标签、tokenizer、preprocessor 和 `.onnx`
- 修改模型后不需要重新 build 镜像

Git 约定：

- `.onnx` 使用 Git LFS 管理
- 其余脚本、标签和轻量配置走普通 Git
