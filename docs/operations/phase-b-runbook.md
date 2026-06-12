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
- 但在新流程语义下，它当前承载的是“问诊准备阶段的基础资料”，不是完整症状筛查或高风险问诊结果。
- EEG 当前冻结边界是：Docker 内保留唯一一份业务侧 `multimodal-service`；不要再把完整 `multimodal-service` 通过宿主机地址作为默认开发链路切出去。

## Windows EEG 默认开发流程

截至 `2026-06-09`，Windows 默认 EEG 开发流程已经切换为：

1. 启动 Docker 主链：
   `docker compose -f infra/compose/docker-compose.dev.yml up -d --build`
2. 真机联调时，在宿主机启动轻量 bridge：
   `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command bridge`
3. 无设备或回归联调时，在宿主机启动 replay：
   `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode simulate`
4. 如需回放真实录制文件：
   `powershell -ExecutionPolicy Bypass -File scripts/start_eeg_tools.ps1 -Command replay -Mode raw -ReplayFile <jsonl路径> -Speed 1.0`

重要约束：

- 默认链路下，`consultation / assessment / risk / gateway` 都固定访问容器内 `http://multimodal-service:8000`
- 不要在正常开发中再设置 `MCS_MULTIMODAL_SERVICE_URL`
- 不要同时启动真实 bridge 和 replay 往同一条 stream 推数据
- 预留的 Jetson bridge 容器仅通过 `infra/compose/docker-compose.jetson-eeg-bridge.yml` 显式启用，Windows 默认开发阶段不要加载它
