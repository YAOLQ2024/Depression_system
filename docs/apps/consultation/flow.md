# `consultation` 应用流程设计

## 1. 当前主流程

1. 用户打开前台
2. 进入登录/注册页
3. 登录成功后请求 `/users/me`
4. 再请求 `/system/bootstrap`
5. 如果 `profile_status = draft`，进入问诊准备页
6. 提交问诊准备后，再次拉取 `bootstrap`
7. 进入“正式问诊入口”占位页，等待后续主链接入

## 2. 后续目标流程

1. 登录成功
2. 完成问诊准备
3. 创建问诊会话
4. 进入数字人交互问诊
5. 按 4 个固定子模块推进
6. 完成后移交量表问诊
7. 量表结束后进入结果与干预链路

## 3. 页面状态流转

认证态：

- `unauthenticated`
- `authenticating`
- `authenticated`

问诊准备态：

- `preparation_draft`
- `preparation_submitting`
- `preparation_completed`

后续问诊态：

- `consultation_idle`
- `consultation_running`
- `consultation_waiting_input`
- `consultation_high_risk_paused`
- `consultation_handoff_to_assessment`

## 4. 异常分支

未登录：

- 任何用户态接口 401 时回退登录页

Bootstrap 加载失败：

- 保留当前页面
- 显示错误 banner
- 允许手动刷新重试

问诊准备提交失败：

- 表单保留原值
- 错误提示不清空
- 不自动跳转

后续问诊异常：

- 与 `consultation-service` 的状态机错误分开展示
- 区分“识别失败”和“服务失败”

## 5. 对正式实现的约束

- 问诊流程必须是有状态流程，不是聊天室式无限消息流
- 患者侧不提供数字医生人设切换
- 量表阶段只接 4 个活跃量表，不把 `SCL-90` 混入当前主链
