# `gateway-service` 服务设计概览

## 1. 概述

`gateway-service` 是浏览器端统一 API 入口，也是当前最关键的前端聚合层。

它的职责不是承载核心业务，而是：

- 接住浏览器请求
- 管理会话 Cookie
- 把请求转发给后端领域服务
- 聚合前端启动所需的 workflow 和配置摘要

## 2. 核心设计结论

- `gateway-service` 只做会话收口、代理转发和轻聚合，不承载领域业务。
- 浏览器统一只连 `gateway-service`，后端领域服务不直接暴露给前端。
- `bootstrap` 是两个应用都依赖的启动接口，稳定性优先级高于普通业务接口。
- 后续即使增加 `consultation-service`、`assessment-service`，也不能把它做成新的业务大单体。

## 3. 职责边界

负责：

- 浏览器会话 Cookie 的写入与删除
- `/auth/*`、`/users/*` 的代理转发
- `bootstrap` 聚合输出
- consultation live snapshot 与 SSE 流式代理
- `workflow` 与数字医生配置目录的只读加载

不负责：

- 用户账号和密码的真实存储
- 问诊准备字段落库
- 问诊状态机执行
- 量表计分
- 风险判断

## 4. 上下游

上游：

- `apps/consultation`
- `apps/operations-console`

下游：

- `identity-service`
- 后续 `consultation-service`
- 后续 `assessment-service`
- 本地 `packages/workflow-resources/`

## 5. 当前实现状态

已实现：

- 登录/注册/退出代理
- `users/me` 查询代理
- `users/me/profile` 更新代理
- `workflow` 与数字医生目录聚合
- consultation 会话创建代理
- consultation 会话状态查询代理
- consultation 问答轮次代理
- consultation live snapshot 代理
- consultation live SSE 代理
- gateway 到 consultation-service 的用户归属透传

待实现：

- assessment 会话代理
- 更清晰的上游错误映射

已知限制：

- 当前真实下游是 `identity-service` 与 `consultation-service`
- 配置目录读取逻辑仍比较原始
- 还没有统一请求追踪标识

## 6. 非目标

- 不把领域逻辑写进 gateway
- 不在 gateway 内直接做风险计算或量表计分
