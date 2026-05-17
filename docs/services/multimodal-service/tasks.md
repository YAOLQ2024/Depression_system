# `multimodal-service` 服务实施任务

## 当前 owner 与协作边界

- 当前 owner（语音转写）：朱睿
- 当前 owner（其他非 EEG）：刘倩
- 当前 owner（EEG 模态与脑电帽硬件）：金伟
- 配合方：主线负责人负责把输出结构接入 `risk-service`、`assessment-service` 与前端链路
- 模块职责：负责多模态会话、采集片段、模态特征和标准化特征包输出

## 当前交付目标

- 先把多模态统一输出格式定住，再逐个接真实模态
- 把“语音转写”、“其他非 EEG 模态”和“EEG 模态 + 设备链路”切成三块可并行子任务
- 最终向 `risk-service` 输出统一的标准特征包，不让下游兼容多套结构

## 可直接认领的任务包

### P0：统一协议与数据模型

- MM-01（刘倩）：设计多模态会话、采集片段、特征包数据模型
- MM-02（朱睿 + 刘倩）：共同固定语音转写、语音特征、表情、姿态等非 EEG 模态的统一返回结构
- MM-03（金伟）：定义 EEG 采集协议、脑电帽接入方式、采样元数据和质量标记
- MM-04（朱睿 + 刘倩 + 金伟）：共同确认最终标准化特征包 Schema

### P1：模态接入与标准输出

- MM-11（刘倩）：实现多模态会话创建接口
- MM-12（朱睿）：实现语音转写接口与 transcript 返回结构
- MM-13（刘倩）：实现语音特征、表情/姿态占位接口
- MM-14（金伟）：实现 EEG 模态输入适配、脑电帽数据采集与标准化输出
- MM-15（朱睿 + 刘倩 + 金伟）：合并输出为统一特征包，并产出示例 payload

### P2：质量控制与调试支持

- MM-21（朱睿 + 刘倩）：增加语音与非 EEG 链路的质量评估、时间同步和重试机制
- MM-22（金伟）：补充 EEG 质量检测、异常标记与设备联调说明
- MM-23（刘倩）：增加后台回放与调试支持

## 依赖与协作约束

- 依赖 `consultation-service` 和 `assessment-service` 提供稳定的会话上下文
- 依赖真实设备、模型或第三方推理组件的输入输出格式明确
- EEG 输出字段必须服从统一 Schema，不能单独发明第二套结果结构
- 非 EEG 模态与 EEG 模态都必须提交样例数据和自测说明

## 验收口径

- `risk-service` 能基于统一特征包消费所有模态，不需要区分开发者来源
- 朱睿负责的语音转写链路、刘倩负责的其他非 EEG 链路、金伟负责的 EEG 链路都能单独自测
- 时间戳、质量标记、模态来源字段完整，足以支撑后续风险分析和调试

## 当前推进状态（2026-05-17）

已完成：

- 非 EEG 四模态模型已并入 `services/multimodal-service/app/models/non_eeg/`
- 已实现本地推理接口与旧版兼容接口
- 已实现 `multimodal_sessions` / `multimodal_captures` / `multimodal_inference_results` / `multimodal_turn_bundles`
- 已实现：
  - `POST /api/v1/multimodal/sessions`
  - `GET /api/v1/multimodal/sessions/{session_id}`
  - `POST /api/v1/multimodal/sessions/{session_id}/warmup`
  - `POST /api/v1/multimodal/sessions/{session_id}/audio-turns`
  - `POST /api/v1/multimodal/sessions/{session_id}/captures/face`
  - `POST /api/v1/multimodal/sessions/{session_id}/captures/pose`
  - `GET /api/v1/multimodal/sessions/{session_id}/live`
  - `GET /api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle`

明确未做：

- ASR 语音转写
- EEG 模态
- 对象存储落盘
- 前端页面接线
- `risk-service` 正式消费
