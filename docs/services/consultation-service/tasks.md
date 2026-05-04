# `consultation-service` 服务实施任务

## 当前 owner 与协作边界

- 当前 owner：主线负责人（仓库维护者）
- 模块职责：负责数字人问诊会话、规则版状态机、轮次记录、问诊结果移交
- 不在本模块内解决：量表计分、最终风险结论、干预编排、报告导出

## 当前交付目标

- 保持四阶段规则问诊链路稳定
- 让问诊结果能稳定移交到量表阶段
- 为后续接入更正式的 ASR 与多模态上下文预留接口，但不引入第二套主链

## 可直接认领的任务包

### P0：基础骨架

- CONSULT-01：维持会话表、问答记录表和 workflow/script 资源装载器稳定
- CONSULT-02：固定状态机最小抽象：`session / stage / node / branch`
- CONSULT-03：维持会话 owner 校验、启动、推进、暂停、移交逻辑

### P1：主链增强

- CONSULT-11：完善 `stage-01` 到 `stage-04` 的规则推进细节
- CONSULT-12：细化正常/沉默/识别失败三类分支与日志
- CONSULT-13：完善高风险中断与人工介入标记
- CONSULT-14：稳定输出量表移交数据，供 `assessment-service` 直接消费

### P2：可观测性与扩展位

- CONSULT-21：接入更正式的 ASR 适配层
- CONSULT-22：增加更细的日志、回放、调试能力
- CONSULT-23：为将来 `llm_engine` 扩展预留抽象，但不启用第二主链

## 依赖与协作约束

- 依赖 `workflow-resources` 稳定
- 依赖 `gateway-service` 代理链路稳定
- 依赖 ASR/语音输入方案明确
- 不允许把量表逻辑或风险计算直接混进本服务

## 验收口径

- 从创建会话到 `handoff_ready` 的链路能通过 API 与前端两侧联调验证
- 会话回放能看出每轮输入、状态推进和暂停原因
- 向 `assessment-service` 输出的数据结构稳定且可复现
