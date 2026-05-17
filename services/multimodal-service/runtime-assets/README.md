# Runtime Assets Layout

这个目录现在不再承载已迁入服务内部的非 EEG 四模态模型资产。

当前约定改为：

- 非 EEG 四模态资产放在：`app/models/non_eeg/`
- 当前只迁入 4 个模态：
  - `text_emotion/`
  - `audio_emotion/`
  - `face_emotion/`
  - `pose_emotion/`
- **不包含 ASR**
- EEG 相关能力后续单独接入，不和这 4 个模态混放

保留这一级目录，是为了给后续仍可能需要的外部协议文件、样例 payload、对象存储说明留位置。
