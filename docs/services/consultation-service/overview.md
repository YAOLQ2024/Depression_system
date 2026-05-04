# `consultation-service` 服务设计概览

## 1. 概述

`consultation-service` 是 MCS 的核心业务服务，负责“数字人交互问诊”整段主链。

它要把老师确认的 4 个子模块真正落成可执行状态机：

1. 初始问候与流程说明
2. 主诉采集
3. 现病史规则式问诊
4. 高风险问题排查

## 2. 核心设计结论

- `consultation-service` 是 MCS 主链里最核心的业务服务，必须先把规则状态机立住。
- 问诊逻辑必须由 `workflow + script` 配置驱动，不能重新写成大量硬编码分支。
- 高风险筛查是独立安全门，不能混进普通追问。
- 当前先做规则版，不引入第二条 LLM 主链。

## 3. 职责边界

负责：

- 创建问诊会话
- 读取 workflow 与 `rule-v1` 剧本
- 驱动问诊节点流转
- 处理正常/沉默/识别失败三类分支
- 生成结构化问诊结果
- 输出量表移交数据

不负责：

- 浏览器认证
- 量表会话管理
- 临床风险最终计算
- 干预推荐

## 4. 上下游

上游：

- `gateway-service`
- `consultation` app

下游：

- `packages/workflow-resources/workflows/consultation-v1.yaml`
- `packages/workflow-resources/interview-scripts/rule-v1/*.yaml`
- 后续 ASR 接口
- PostgreSQL

## 5. 当前实现状态

已实现：

- PostgreSQL + Alembic migration
- `consultation_sessions` / `consultation_turns` 持久化
- workflow / script 资源装载器
- 四段规则问诊的最小状态机骨架
- 创建问诊会话
- 启动正式问诊
- 获取会话状态
- 提交问答轮次
- gateway 透传的用户归属校验

待实现：

- 更精细的字段抽取与结构化策略
- 更完整的重试 / 回退 / 调试追踪
- 正式 ASR 适配层
- 量表阶段更完整的 handoff 细节

## 6. 非目标

- V1 不依赖 LLM 主链
- 不做患者侧数字医生选择
- 不把量表逻辑混入问诊服务
