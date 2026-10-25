# `gateway-service` 服务实施任务

## 当前 owner 与协作边界

- 当前 owner：主线负责人（仓库维护者）
- 模块职责：负责统一入口、会话鉴权、前端聚合、错误码与响应结构统一
- 不在本模块内解决：量表计分、风险判断、干预策略等领域逻辑

## 当前交付目标

- 保持当前登录、资料、问诊主链代理稳定
- 为后续量表、风险、干预、回顾链路提供统一网关接入
- 把请求追踪、错误处理、日志结构固定下来，减少多人联调成本

## 可直接认领的任务包

### P0：基础稳定性

- GATEWAY-01：固定当前代理链路、Cookie 规则、错误码与响应结构
- GATEWAY-02：维持 `consultation-service` 代理链路稳定，禁止把领域逻辑塞进网关
- GATEWAY-03：为 `assessment-service`、`risk-service`、`intervention-service`、`followup-service` 预留 client 与 router 分层

### P1：主链扩展

- GATEWAY-11：接入量表会话创建、状态读取、单题提交、聚合完成接口
- GATEWAY-12：接入后台记录查询和导出入口
- GATEWAY-13：增加 `request_id`、`trace_id`、统一 access log 与错误日志结构

### P2：高级网关能力

- GATEWAY-21：支持 consultation live 的 SSE/流式转发
- GATEWAY-22：增加更细粒度的角色权限映射
- GATEWAY-23：增加配置缓存、资源热更新和更明确的降级策略

## 依赖与协作约束

- 依赖 `identity-service` 的稳定性
- 依赖 workflow 资源目录结构稳定
- 各领域服务必须先固定输入输出结构，再由网关接入，不允许边实现边频繁改返回格式

## 验收口径

- 浏览器端不需要直接访问任何内部领域服务端口
- 网关只负责鉴权、转发、聚合和响应封装，不承担领域计算
- 新服务接入时只新增 client/router/schemas，不把逻辑散落到现有模块里
- consultation 页面可通过 gateway 订阅 `/consultations/{id}/multimodal/live/stream`

## 2026-10-22 EEG 历史与解释代理

- 为多模态会话新增 EEG 窗口历史、解释任务、详情及历史列表代理。
- 保持现有登录态及 X-MCS-User-Id 透传，由领域服务核对资源归属。
