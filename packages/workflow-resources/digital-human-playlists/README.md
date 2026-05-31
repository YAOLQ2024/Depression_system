# Digital Human Playlists

这个目录存放数字人固定视频问诊清单。

它的职责不是描述 LLM prompt，也不是保存视频二进制，而是定义：

- 问诊四阶段的固定顺序
- 每个阶段包含哪些固定问题项
- 每个问题项对应哪个视频资源
- 每个问题项对应的权威问题文本

## 当前契约

当前 manifest 使用：

- `manifest_contract: digital-human-playlist/v1`

示例文件：

- `consultation-v1.yaml`

## 顶层字段

- `workflow_id`
  - 对应问诊 workflow，例如 `consultation-v1`
- `manifest_contract`
  - 当前固定为 `digital-human-playlist/v1`
- `playlist_version`
  - 这份视频清单本身的内容版本，不等于数据库 schema 版本
- `manifest_status`
  - 例如 `placeholder`、`draft`、`final`
- `delivery_mode`
  - 当前固定为 `fixed-video-playlist`
- `notes`
  - 仅供人工说明，不参与业务判断

## stages 字段

每个 stage 必须包含：

- `stage_id`
- `stage_label`
- `stage_order`
- `question_items`

可选字段：

- `stage_intro_text`
- `stage_intro_video_uri`

约束：

- `stage_order` 在一个 workflow 内必须唯一
- `stages` 的逻辑顺序以 `stage_order` 为准
- `stage_intro_*` 用于在进入某个量表阶段时先播报一段引导视频，不占用实际题目序号

## question_items 字段

每个问题项必须包含：

- `question_key`
- `order`
- `node_id`
- `video_asset_id`
- `video_uri`
- `question_text`
- `response_required`

可选字段：

- `subtitle_text`

约束：

- `question_key` 在整个 workflow 内必须唯一
- `order` 在所属 stage 内必须唯一
- `video_uri` 只引用视频位置，不保存视频文件本体
- `question_text` 是权威业务文本
- `subtitle_text` 如果为空，前端展示层可直接回退使用 `question_text`

## question_text 与 subtitle_text 的区别

- `question_text`
  - 必填
  - 用于和用户原始语音、转写文本、后续多模态结果做一一绑定
  - 是数据库落库时应保存的问题文本
- `subtitle_text`
  - 可选
  - 用于视频展示时的字幕覆盖
  - 如果与 `question_text` 相同，可以不单独提供

## 与服务内部字段的关系

manifest 面向业务语义，优先使用：

- `question_items`
- `question_key`
- `question_text`

后续 `consultation-service` 读取时，可以在内部映射成当前更接近既有实现的字段，例如：

- `question_key -> prompt_key`
- `question_text -> prompt_subtitle_text` 或 `question_text`

这样可以同时满足：

- 对产品和前端语义清晰
- 对后端现有代码改动可控

## 存储边界

- 视频文件本体：
  - 放静态目录或对象存储
- manifest：
  - 只保存视频元数据和问题文本
- 数据库：
  - 保存最终被会话使用的问题文本、视频元数据引用、用户回答音频 URI、ASR transcript 等
