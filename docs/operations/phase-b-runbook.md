# Phase B Runbook

Phase B 目标：

- `consultation` 前端壳可登录、完成问诊准备、进入正式问诊入口
- `operations-console` 可登录并查看后台概览
- `gateway-service` 负责 cookie 会话与前端 API 收口
- `identity-service` 负责注册、登录、角色和问诊准备基础资料

## 本地端口

- `consultation`: `http://127.0.0.1:3000`
- `operations-console`: `http://127.0.0.1:3001`
- `gateway-service`: `http://127.0.0.1:8080`
- `identity-service`: `http://127.0.0.1:8011`

## 示例账号

- `admin@mcs.local / Admin123!`
- `researcher@mcs.local / Research123!`
- `participant@mcs.local / Participant123!`

## 关键接口

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users/me`
- `PUT /api/v1/users/me/profile`
- `GET /api/v1/system/bootstrap`
- `GET /api/v1/catalog/doctor-personas`
- `GET /api/v1/catalog/workflow-summary`

## 当前实现边界

已完成：

- 登录/注册
- cookie 会话
- 当前用户查询
- 问诊准备字段保存
- 默认数字医生配置目录读取
- 工作流概要读取
- 受试者前端壳
- 管理后台前端壳

未完成：

- consultation-service 规则版状态机执行
- assessment-service 量表逐题作答
- risk-service 风险计算
- intervention-service 干预执行
- followup-service 追踪闭环

## 说明

当前仓库内已具备 Phase B 代码，但本机会不会立即可运行取决于是否已安装：

- `fastapi`
- `uvicorn`
- `pydantic`
- `PyYAML`

如果环境缺依赖，先安装对应 requirements，再启动服务或使用 Docker Compose。

## 工程检查

- `make compose-config`
- `make phase-b-check`

前端默认通过 `client/config.js` 读取浏览器端 API 地址，默认值是 `http://127.0.0.1:8080/api/v1`。

补充说明：

- 目前 `PUT /api/v1/users/me/profile` 这个接口名称先保持不变。
- 但在新流程语义下，它当前承载的是“问诊准备阶段的基础资料”，不是完整现病史或高风险问诊结果。
