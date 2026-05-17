# `multimodal-service` 服务实施任务

## 当前 owner 与协作边界

- 当前 owner（语音转写与 `audio_uri` / `transcript_text`）：朱睿
- 当前 owner（其他非 EEG）：刘倩
- 当前 owner（EEG 模态与脑电帽硬件）：金伟
- 主线负责人负责前端接线、主库回写、主链状态推进与 `risk-service` 对接

## 当前交付目标

- 让非 EEG 接口对齐 `Step 4D` 规范并能实际接入主系统
- 固定前端看板与 turn 级 bundle 的消费字段
- 保留 EEG 扩展位，但不让 EEG 阻塞非 EEG 接入

## 当前推进状态（2026-05-17）

### 已完成

- 非 EEG 四模态模型已并入 `services/multimodal-service/app/models/non_eeg/`
- 已实现多模态会话、采样明细、推理结果、turn bundle 的基础落库
- 已实现 `audio-turns` 后内部补齐：
  - `speech_emotion`
  - `text_emotion`
- 已实现 `captures/face` / `captures/pose` 的 Step 4D 表单协议接入
- 已实现 `/live` 的稳定返回结构：
  - `speech`
  - `text`
  - `face`
  - `pose`
  - `updated_at`
- 已实现 `/turns/{turn_id}/bundle` 的 Step 4D 汇总结构：
  - `speech_features`
  - `text_features`
  - `face_features`
  - `pose_features`
- 已实现 turn 级 face / pose 汇总
- 已实现 session 级 face / pose 汇总写入 `session_summary_payload`

### 尚未完成

- EEG 模态接入
- Dolphin ASR
- MinIO 音频落盘
- 前端页面正式联调
- `risk-service` 正式消费与验收
- face / pose 质量标记的更细粒度算法

## 下一阶段任务

### P1

- MM-11：和 `gateway-service` / `consultation-service` 对齐 `audio-turns` 入参
- MM-12：补充 `/live` 与 `/bundle` 的联调样例
- MM-13：确认 face / pose 的窗口统计规则是否继续沿用当前实现

### P2

- MM-21：把 face / pose 的 `blur` / `low_light` / `body_cutoff` / `motion_blur` 从占位值升级为真实质量评估
- MM-22：补充 EEG 对齐统一 Schema
- MM-23：补齐更完整的接口与聚合测试

## 验收口径

- 前端右侧看板只轮询 `/live` 就能拿到稳定结构
- turn 结束后主链只读取 `/bundle` 就能拿到固定字段
- `captures/face` / `captures/pose` 能持续收帧并回写细粒度结果
- `audio-turns` 后能补齐 `speech_emotion` / `text_emotion`
- face / pose 的 turn 级汇总和 session 级汇总可持续更新
