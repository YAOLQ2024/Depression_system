# `consultation` 应用实施任务

## 当前 owner 与协作边界

- 当前 owner：主线负责人（仓库维护者）
- 模块职责：负责患者侧页面、交互流程、视觉风格、前端状态管理与 `gateway-service` 接入
- 不在本模块内解决：量表计分、风险分层、干预编排、回顾导出，这些能力分别由下游服务承担

## 当前交付目标

- 把现有可运行壳页逐步收敛为正式前端应用
- 保持视觉风格贴近旧 `Depression`，但实现方式改为前后端分离
- 确保浏览器只访问 `gateway-service`，不直接访问领域服务

## 可直接认领的任务包

### P0：前端工程化收口

- APP-CONSULT-01：把当前静态页面迁移到 `React + TypeScript + Vite + TSX`
- APP-CONSULT-02：建立患者端路由骨架、布局组件、全局状态与 API 调用层
- APP-CONSULT-03：整理设计变量、字体、卡片、表单、状态提示组件，视觉语言对齐旧系统

### P1：主链页面落地

- APP-CONSULT-11：实现正式版登录/注册页
- APP-CONSULT-12：实现问诊准备页与资料校验
- APP-CONSULT-13：实现正式问诊页，接入 `consultation-service` 当前状态与轮次提交
- APP-CONSULT-14：实现异常状态页，包括沉默、识别失败、高风险暂停

### P2：量表与后续阶段页面

- APP-CONSULT-21：实现 4 个活跃量表作答页与进度恢复
- APP-CONSULT-22：实现决策结果页、干预执行页、回顾与再评估页
- APP-CONSULT-23：补充断线恢复、空态页、错误页与审计提示

## 依赖与协作约束

- 依赖 `gateway-service` 提供稳定的 Cookie 会话与聚合 API
- 依赖 `consultation-service` 提供问诊状态机接口
- 依赖 `assessment-service` 提供 4 个量表会话与提交接口
- 页面结构、字段命名、状态码解释必须与 `docs/services/*/api-and-data.md` 保持一致

## 验收口径

- 患者端主链能从登录一路走到量表入口，不需要直接访问内部服务端口
- 前端 UI 风格明显继承旧 `Depression`，但代码结构是前后端分离的 React 工程
- 所有 API 调用集中在前端 API 层，不在页面组件里散写请求逻辑
