# `risk-service` 服务设计概览

## 1. 概述

`risk-service` 负责 MCS 中“临床决策”阶段的规则执行与风险分层输出。

它接收问诊结构化结果、量表结果和多模态特征，按风险规则生成风险等级、解释、建议和干预入口数据。

## 2. 核心设计结论

- `risk-service` 是“临床决策”阶段的核心服务，但它基于规则和输入聚合做判断，不直接承担问诊或量表逻辑。
- 高风险筛查结果具有优先级，可以在量表全部完成前触发安全升级。
- 多模态信号只能作为辅助证据，不能单独决定最终风险等级。
- 风险服务的输出必须结构化，既能给前端展示，也能无缝移交给 `intervention-service` 和 `followup-service`。

## 3. 职责边界

负责：

- 汇总问诊结构化结果
- 汇总量表聚合结果
- 汇总多模态特征包
- 加载风险规则并执行
- 输出风险等级、风险解释、转诊建议和生活建议
- 输出干预入口数据

不负责：

- 数字人问诊推进
- 量表逐题作答与计分
- 干预内容实际执行
- 回顾记录和再评估调度

## 4. 上下游

上游：

- `consultation-service`
- `assessment-service`
- `multimodal-service`

下游：

- `intervention-service`
- `followup-service`
- 后续报告导出链路
- `packages/workflow-resources/risk-rules/consultation-v1.yaml`

## 5. 当前实现状态

已实现：

- 风险规则装载器
- `risk_evaluation` / `risk_trigger` 持久化模型与迁移
- `POST /api/v1/risk/evaluations`
- `GET /api/v1/risk/evaluations/{evaluation_id}`
- `GET /api/v1/risk/evaluations/{evaluation_id}/explanations`
- Gateway 风险评估转发接口
- 高风险硬触发逻辑
- 量表聚合 + 多模态辅助的抑郁分层逻辑
- 干预入口 payload 生成
- `missing_inputs` / `pending_integrations` 联调标记

待实现：

- 人工复核工作流真正落库与覆盖逻辑
- EEG 正式模态接入
- 多模态最终特征包正式接口接入
- 规则版本切换与后台配置化管理

已知限制：

- 当前风险规则文件已固化初版权重与分层带，但仍需要临床联调校准阈值
- 人工复核接口目前只做了预留，返回 `501`
- 多模态当前先消费显式 `multimodal_feature_bundle` 或 `live snapshot`，尚未接入最终 bundle
- EEG 模态尚未提供可稳定消费的统一输出

## 6. 非目标

- 不把最终干预执行逻辑写进本服务
- 不在这里做患者端页面展示逻辑
- 不把多模态模型推理逻辑塞进风险服务
