# Depression 项目现状评估与重构基线

本文档用于后续重构 `/home/ZR/data2/Depression` 时快速恢复上下文，重点回答 4 个问题：

1. 这个项目现在到底是什么。
2. 它当前真实的技术架构是什么，而不是“计划中想变成什么”。
3. 它为什么会显得结构混乱。
4. 如果参考 `aic-coralreef` 重构，哪些部分值得保留，哪些必须拆掉或隔离。

---

## 1. 一句话结论

`Depression` 当前不是一个“前后端分离的整洁系统”，而是 4 层东西叠在一起：

1. 旧的 Flask + Jinja 单体 Web 应用。
2. 同一进程内新增的 `/api/v1/*` 模块化尝试。
3. 已经拆出去的少量独立推理服务（尤其是 `multimodal_service`）。
4. 挂在仓库旁边、又和主系统强耦合的 `EmoLLM` / RAG / 参考服务项目。

所以它看起来乱，不是单纯“代码写得差”，而是两代架构同时存在：

- 第一代是“本地部署 demo/课题系统式”的 Flask 单体。
- 第二代是“想往模块化 API + 多服务方向走”的半成品。

---

## 2. 这个项目是做什么的

从 [`depression/项目说明.txt`](/home/ZR/data2/Depression/depression/项目说明.txt) 和 [`depression/docs/project_handover_20260308.md`](/home/ZR/data2/Depression/depression/docs/project_handover_20260308.md) 看，项目定位是：

- 抑郁情绪筛查与心理咨询 Web 系统
- 支持账号登录/注册
- 支持量表筛查，当前至少包括 SDS、PHQ-9、GAD-7
- 支持“问卷 + 文本/语音/表情/姿态/脑电”的多模态辅助评估
- 支持 AI 咨询与会话总结
- 支持本地 LLM + RAG + 本地多模态推理

更准确地说，这不是单纯聊天系统，而是一个闭环：

`量表筛查 -> 风险分层 -> 引导对话 -> 干预建议 -> 历史记录/报告`

这条闭环在设计文档里已经很清楚，尤其体现在：

- [`depression/docs/system_modular_api_design_v1_20260401.md`](/home/ZR/data2/Depression/depression/docs/system_modular_api_design_v1_20260401.md)
- [`depression/docs/system_module_master_table_v1_20260401.md`](/home/ZR/data2/Depression/depression/docs/system_module_master_table_v1_20260401.md)
- [`depression/docs/team_api_collaboration_spec_v1_20260403.md`](/home/ZR/data2/Depression/depression/docs/team_api_collaboration_spec_v1_20260403.md)

问题不在目标，而在实现：当前实现没有把这条链真正拆成清晰服务。

---

## 3. 仓库级真实结构

`/home/ZR/data2/Depression` 根目录不是一个单一应用，而是多个项目混放：

### 3.1 主项目：`depression/`

这是当前真正提供 Web 系统能力的目录，里面又分成几层：

- `my_flask_app/`
  当前主 Web 应用，Flask 单体入口、模板、静态资源、SQLite、旧业务路由都在这里。
- `new_features/`
  在原 Flask 单体上增量挂载的新模块，试图标准化为 `/api/v1/*`。
- `services/multimodal_service/`
  已拆出的 FastAPI 推理服务，提供文本/语音/表情/姿态 4 模态 API。
- `scripts/`
  本地启动 LLM、RAG、Flask 应用的一套脚本。
- `docs/`
  模块化 API 设计、交接文档、协作规范、OpenAPI 草稿。
- `models/`
  模型文件和本地推理资源。

### 3.2 外挂项目：`EmoLLM/`

这是另一个大项目，不应与 Web 主系统物理混在一起，但当前运行依赖它提供：

- 本地 LLM 推理
- RAG 服务
- 部分训练、数据和实验资产

### 3.3 参考资产：`reference_services/`

这里主要是参考用服务，例如 EEG Windows FastAPI 服务，不属于当前主 Web 应用的干净运行骨架。

### 3.4 结构混乱的根源

如果未来重构，首先要承认一个事实：

- `Depression` 仓库级别已经混成“产品代码 + 实验代码 + 推理资产 + 参考实现 + 历史残留”的总堆栈。

所以后续不能直接“在这个目录里一点点修”，而应该先做逻辑拆箱：

- 平台主应用
- 业务服务
- 模型/推理服务
- 实验/训练资产
- 历史废弃物

---

## 4. 当前技术栈

### 4.1 后端

- Python
- Flask
- FastAPI
- Uvicorn
- SQLite
- 原生 SQL 封装（不是 ORM）

关键入口：

- Flask 主入口：
  [`depression/my_flask_app/app.py`](/home/ZR/data2/Depression/depression/my_flask_app/app.py)
- Flask 应用工厂：
  [`depression/my_flask_app/flask_app/__init__.py`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/__init__.py)
- SQLite 工具：
  [`depression/my_flask_app/utils/db.py`](/home/ZR/data2/Depression/depression/my_flask_app/utils/db.py)
- 多模态 FastAPI：
  [`depression/services/multimodal_service/api_server.py`](/home/ZR/data2/Depression/depression/services/multimodal_service/api_server.py)

### 4.2 前端

- Flask + Jinja2 模板
- 原生 HTML/CSS/JS
- CDN 方式引入 Tailwind CSS
- CDN 方式引入 Alpine.js
- 少量原生 JS API 封装

关键页面/资源：

- 模板基座：
  [`depression/my_flask_app/flask_app/templates/base.html`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/base.html)
- 登录页：
  [`depression/my_flask_app/flask_app/templates/login.html`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/login.html)
- 主工作台：
  [`depression/my_flask_app/flask_app/templates/main.html`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/main.html)
- 量表前端 API 辅助：
  [`depression/my_flask_app/flask_app/static/js/scale_assessment_api.js`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/static/js/scale_assessment_api.js)

### 4.3 AI / 推理 / 模型侧

- 本地 LLM 推理：`lmdeploy`
- RAG 服务：单独 `uvicorn` 启动
- ONNX Runtime GPU：多模态服务
- SiliconFlow 兼容接口调用逻辑
- Tavily 联网搜索能力接入痕迹

关键参考：

- [`depression/start_app_gpu.py`](/home/ZR/data2/Depression/depression/start_app_gpu.py)
- [`depression/my_flask_app/utils/emollm_client.py`](/home/ZR/data2/Depression/depression/my_flask_app/utils/emollm_client.py)
- [`depression/services/multimodal_service/README.md`](/home/ZR/data2/Depression/depression/services/multimodal_service/README.md)

### 4.4 基础设施层

当前基础设施比较弱，主要是：

- `.env` 配置
- shell 启动脚本
- 本地日志目录
- 健康检查脚本

而不是：

- Docker Compose
- Kubernetes
- Nginx 网关编排
- 数据库迁移框架
- 服务注册/配置中心

---

## 5. 前后端分离现状

### 5.1 当前结论：没有真正做到前后端分离

虽然项目里有 `/api/v1/*`，但它仍然不是 `aic-coralreef` 那种真正意义上的前后端分离。

当前页面主链依然是：

`浏览器 -> Flask 路由 -> render_template(...) -> Jinja 页面`

关键证据：

- `account.py`、`main.py`、`test.py`、`psychological_counseling.py` 大量直接 `render_template(...)`
- `scale_assessment/api.py`、`text_dialogue/api.py`、`intervention/api.py` 这批“新模块”也同时包含“页面路由 + API 路由”
- 页面使用 session 直接驱动模板展示，例如 sidebar 中直接读 `session["userinfo"]`

### 5.2 当前更接近什么形态

它更接近“服务端渲染模板站点 + 同进程 JSON 接口补丁”的混合形态，而不是：

- 前端独立工程
- 后端独立 API 服务
- 前端只通过 HTTP/JSON 访问后端

### 5.3 和 `aic-coralreef` 的关键差异

`aic-coralreef` 的核心是：

- Host/Portal 负责入口和壳层
- 业务应用独立 `client/server`
- 网关负责访问路径与统一鉴权
- 用户和应用注册走平台服务

`Depression` 当前没有这些边界。它的“UI、业务逻辑、鉴权、DB、部分 API、部分对外服务调用”基本仍在一个 Flask 应用里。

---

## 6. 当前后端分层情况

### 6.1 旧主线：Flask 单体

最传统的一层是 `my_flask_app/`：

- `views/account.py`：登录、注册、用户信息
- `views/main.py`：工作台、历史记录、详情页
- `views/test.py`：SDS、多模态采集/提交相关旧逻辑
- `views/psychological_counseling.py`：咨询页与聊天接口

特点：

- 路由、业务逻辑、数据库访问耦合在一起
- 直接依赖 `utils/db.py`
- 使用 `session["userinfo"]` 做登录态
- 视图函数直接返回页面或 JSON

### 6.2 新主线：`new_features/` 模块化尝试

`new_features/` 是现在最值得保留的方向，但还没有完成服务化。

目前比较明确的模块有：

- `api_v1`
- `scale_assessment`
- `risk_assessment`
- `text_dialogue`
- `intervention`
- `assessment_context`
- `session_summary_skill`
- `skill_router`
- `chat_intent_router`

其中 `api_v1.py` 明确声明了规划中的顶层模块和能力，但实现状态仍是：

- `/api/v1/health`
- `/api/v1/meta`
- 若干模块级 API

它更像“统一命名规范入口”，不是“真正网关”。

### 6.3 已经独立出的服务

目前相对清晰、最接近独立服务的，是：

- `services/multimodal_service/`

它提供：

- `POST /api/v1/text/infer`
- `POST /api/v1/audio/infer`
- `POST /api/v1/emotion-recognition/frame-infer`
- `POST /api/v1/pose/frame-infer`
- `GET /health`

这部分已经具备“独立部署服务”的雏形，后续应继续保持独立，而不是再塞回 Flask。

---

## 7. 网关、权限、鉴权、用户管理现状

### 7.1 网关：几乎没有真正网关

项目里虽然有 `api_v1.py`，但它不是 `aic-coralreef` 那种 Nginx + Gateway/BFF 级别的网关。

它当前主要做的是：

- 暴露统一入口的 `health/meta`
- 给模块命名和流程做发现说明

没有看到成熟的：

- 路由聚合层
- 统一 token 校验层
- 限流/配额
- 服务注册发现
- 外部/内部 API 分层

### 7.2 鉴权：Session 鉴权，且实现较原始

在 [`depression/my_flask_app/flask_app/__init__.py`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/__init__.py) 中：

- `before_request(auth)` 负责统一检查
- 放行 `/login`、`/register`、静态资源和部分 `/api/v1/* health/meta`
- 其余请求依赖 `session.get("userinfo")`

问题：

- `app.secret_key = 'aaaaaaaaaa'` 是硬编码
- 没有 JWT
- 没有 access token / refresh token
- 没有独立 auth service
- 没有统一权限声明模型

### 7.3 用户管理：SQLite 表级实现

当前用户信息在 [`depression/my_flask_app/utils/db.py`](/home/ZR/data2/Depression/depression/my_flask_app/utils/db.py) 中初始化：

- 表：`userinfo`
- 字段包括 `name/mobile/password/email/real_name/sex/number/history/role`

在 [`depression/my_flask_app/flask_app/views/account.py`](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/views/account.py) 中：

- 登录直接用用户名/手机号 + 明文密码查询
- 注册直接插入 SQLite
- 登录成功后整行 `userinfo` 放进 session

问题：

- 密码不是现代安全实现
- 没有用户域服务
- 没有组织/租户概念
- `role` 只有很轻的管理员/普通用户区分
- 权限没有形成统一 RBAC 策略

### 7.4 权限：只有轻量角色，不是系统级权限架构

页面模板里会根据 `session["userinfo"]["role"]` 显示“管理员/普通用户”，但这不是完整权限系统。

和 `aic-coralreef` 相比，当前项目缺失：

- 平台用户中心
- 组织/团队/应用授权模型
- 服务级权限声明
- 网关级鉴权透传
- 统一用户身份与资源权限映射

---

## 8. 数据层现状

### 8.1 主数据库：SQLite

当前主库是：

- `depression/my_flask_app/depression.db`

这是典型单机本地库，适合 demo/实验，不适合平台化。

### 8.2 数据访问方式：手写 SQL + 简单 helper

`utils/db.py` 提供：

- `fetch_one`
- `fetch_all`
- `insert`
- `update`

没有 ORM，也没有 repository/DAO 的统一边界。

### 8.3 迁移方式：手写 `ALTER TABLE`

`migrate_database()` 会在应用启动时检查字段是否存在，不存在就 `ALTER TABLE ADD COLUMN`。

这说明当前数据库演进方式是：

- 应用级临时迁移
- 不是 Alembic / migration framework

### 8.4 当前已出现的数据分层迹象

相对更好的部分出现在 `new_features/scale_assessment/repository.py` 等模块里：

- `scale_assessment_records`
- `scale_assessment_drafts`

说明新模块已经开始尝试“模块自带 repository”，这条思路是对的，值得保留。

---

## 9. 页面设计与前端工程化现状

### 9.1 页面设计

当前页面视觉并不算完全原始，近几次改动已经在向现代化模板靠近：

- `base.html`、`login.html`、`main.html` 使用 Tailwind 风格设计
- 有明确卡片、渐变、图标、响应式布局
- 使用 Alpine.js 处理部分交互

但这依然是“模板驱动 UI”，不是独立前端工程。

### 9.2 当前前端的真实边界

当前前端没有：

- `package.json`
- Vite / Webpack / Next.js / React / Vue 工程
- 独立构建产物目录
- 组件化前端架构

说明页面层仍然归属于 Flask 应用，而不是独立部署的 Web client。

### 9.3 这意味着什么

如果后续要保留现有功能并重构，页面层最好不要继续在 Jinja 模板上叠功能，而应考虑：

- 把 Web 前端单独抽为一个独立 client
- 与后端只通过 API 通信
- 让 Flask/Jinja 模板逐步退场，而不是继续扩展

---

## 10. 调试、启动、运行方式

### 10.1 当前运行模式

根据 [`depression/docs/project_handover_20260308.md`](/home/ZR/data2/Depression/depression/docs/project_handover_20260308.md)，当前典型运行是 3 个服务：

1. LLM 服务：`lmdeploy`，端口 `8000`
2. RAG 服务：`uvicorn rag_official_api:app`，端口 `8001`
3. Flask 应用：`python3 start_app_gpu.py`，端口 `5000`

再加上一个经常被自动拉起或手工检查的：

4. 多模态服务：默认 `8010`

以及可选 EEG：

5. EEG 服务：默认 `8020`

### 10.2 当前运维方式

运维主要靠脚本：

- [`depression/scripts/start_stack.sh`](/home/ZR/data2/Depression/depression/scripts/start_stack.sh)
- [`depression/scripts/stop_stack.sh`](/home/ZR/data2/Depression/depression/scripts/stop_stack.sh)
- [`depression/scripts/check_stack.sh`](/home/ZR/data2/Depression/depression/scripts/check_stack.sh)
- [`depression/scripts/watch_stack_logs.sh`](/home/ZR/data2/Depression/depression/scripts/watch_stack_logs.sh)

### 10.3 `start_app_gpu.py` 的意义

[`depression/start_app_gpu.py`](/home/ZR/data2/Depression/depression/start_app_gpu.py) 不是一个简单入口，它还承担了：

- 环境预检
- 模型/推理运行时检查
- `multimodal_service` 可用性检查
- 本地服务自动拉起
- 健康检查辅助

这说明当前“应用启动”和“本地运维编排”混在一起了。

后续重构时这部分应该往：

- Docker Compose
- supervisor/systemd
- 或单独 ops 脚本层

迁移，而不是继续由应用入口负责。

---

## 11. 容器化现状

### 11.1 当前基本没有形成容器化骨架

在主项目范围内，没有看到成熟的：

- `Dockerfile`
- `docker-compose.yml`
- 按服务拆分的容器定义
- 容器内数据库/网关/应用编排

这与 `aic-coralreef` 的容器化差异非常大。

### 11.2 当前更像什么

当前是：

- 本地多 Python 环境
- 多进程脚本启动
- 端口手工协调
- 日志本地落盘

这适合实验，但不利于复制部署、多人联调和清晰边界管理。

---

## 12. 哪些模块值得保留

### 12.1 最值得保留的不是“旧页面”，而是“新模块的业务边界”

当前最有价值的部分是这些模块化趋势：

- `new_features/scale_assessment/`
- `new_features/risk_assessment/`
- `new_features/text_dialogue/`
- `new_features/intervention/`
- `new_features/assessment_context/`
- `new_features/session_summary_skill/`
- `new_features/skill_router/`
- `services/multimodal_service/`

### 12.2 其中成熟度最高的是 `scale_assessment`

它已经具备：

- 量表定义
- 规则计分
- 落库
- 页面/API 并存
- 清晰的 repository / engine 分层趋势

这个模块很适合作为重构时第一批拆分对象。

### 12.3 还值得保留的能力资产

- `emollm_client.py` 中已有的 LLM/RAG/联网搜索接入经验
- `session_summary_skill` 的 skill 化思路
- `chat_intent_router` 的意图分流思路
- `multimodal_service` 作为外部推理服务的边界

---

## 13. 哪些部分应视为过渡层或待淘汰层

以下部分不适合作为未来核心架构继续扩展：

- `my_flask_app/views/test.py`
  旧时代“大杂烩”业务逻辑聚集地。
- 基于 `render_template` 的整站模板路由继续膨胀
- `utils/db.py` 这种全局 SQLite helper 作为长期数据层
- 在应用启动过程中顺手做 schema patch 的迁移方式
- 硬编码 secret/session 方案
- 把 `EmoLLM` 整个项目与主 Web 代码继续物理揉在一起

这些东西可以作为兼容层暂时保留，但不应成为新架构基座。

---

## 14. 为什么它会让人感觉“狗屎结构”

如果用工程语言总结，主要原因有 7 个：

1. 仓库边界不清。
   `depression`、`EmoLLM`、`reference_services` 混在一个仓库里，但生命周期和职责完全不同。

2. 两代架构叠加。
   旧 Flask 模板单体没退场，新 `/api/v1` 模块又加上去了。

3. 页面与业务未分离。
   新模块里很多文件同时做页面路由、API 路由和业务编排。

4. 鉴权和用户域过于原始。
   Session + SQLite + 明文密码，无法支撑真正平台化。

5. 数据层演进无制度化。
   没有 migration framework，靠应用启动时补字段。

6. 运行编排和应用入口耦合。
   `start_app_gpu.py` 同时做应用启动、服务探测、推理环境兜底。

7. 服务拆分只拆了一半。
   多模态服务已经独立，但核心 Web/业务层仍是单体。

---

## 15. 对照 `aic-coralreef`，最值得借鉴什么

不要机械照搬 `aic-coralreef` 的所有业务细节，但它的骨架非常值得借：

### 15.1 借它的“边界感”

最该学的是：

- 平台入口层
- 统一网关层
- 公共身份/应用注册/计量等平台服务
- 业务应用独立 client/server
- 容器化与环境编排

### 15.2 套到 `Depression` 上的推荐目标形态

后续更合理的目标应该接近：

1. `portal-web`
   独立前端应用，负责登录后工作台、量表、咨询、历史、管理页。

2. `gateway/bff`
   统一入口，负责认证、路由聚合、会话透传、对前端的 API 整形。

3. `auth-service`
   统一用户、登录、密码、角色、会话/JWT。

4. `assessment-service`
   量表、问卷、结果、草稿、流程编排。

5. `dialogue-service`
   咨询对话、会话记录、skill router、意图分流。

6. `risk-service`
   风险分层、规则引擎、安全建议。

7. `intervention-service`
   干预计划与推荐逻辑。

8. `multimodal-service`
   保持独立，继续做推理 API。

9. `llm-adapter` / `rag-service`
   单独对接 LLM、RAG、联网搜索。

10. `report-service`
    历史记录、报告生成、趋势聚合。

注意：

- 不一定要一步到位做成复杂微服务。
- 但至少要先做到“前端独立 + 网关/BFF + 业务服务按域拆分”。

---

## 16. 对 `Depression` 的重构建议顺序

### 第一阶段：先拆边界，不急着大改功能

建议先做“结构重构”，不是“算法重写”：

1. 从仓库里明确划分：
   - 平台主应用
   - 推理服务
   - LLM/RAG 适配层
   - 实验资产

2. 冻结旧 Flask 页面功能，避免继续往 `views/*.py` 里堆逻辑。

3. 抽出统一 API 契约，以 `new_features` 的模块命名为基础。

### 第二阶段：先拆最成熟模块

优先级建议：

1. `scale_assessment`
2. `risk_assessment`
3. `text_dialogue`
4. `intervention`

原因：

- 这 4 个模块已经在设计文档和 `/api/v1/*` 命名上形成闭环。

### 第三阶段：再做身份和入口统一

重点补齐：

- 独立认证方案
- 用户表与密码安全
- JWT 或统一 session/token 方案
- gateway/bff
- 前端独立工程

### 第四阶段：最后再清理历史兼容层

最后处理：

- 旧 `test.py`
- 旧模板路由
- 老式 SQLite helper
- 启动入口里的编排逻辑

---

## 17. 当前我对“可直接迁移”的判断

### 可以直接吸收到新架构的

- 模块命名体系：`assessment / risk-assessment / text-dialogue / intervention`
- `health/meta` 统一接口习惯
- 量表评分规则
- 风险分层规则雏形
- 会话总结 skill 机制
- 多模态独立 API 服务
- LLM/RAG 接入经验

### 只能参考，不能原样迁移的

- Flask 模板页面
- `session["userinfo"]` 鉴权
- SQLite 全局 helper
- 在一个进程内混合页面渲染和 API 编排
- 启动脚本兼任运维编排

### 应明确隔离的

- `EmoLLM/` 大量训练/实验/模型资产
- `reference_services/`
- 历史残留 NPU 文件

---

## 18. 最终判断

`Depression` 不是“从零重写才有救”，也不是“继续在现有 Flask 上修修补补就行”。

更准确的策略应该是：

- 保留现有业务能力与部分新模块实现
- 放弃当前单体承载方式
- 参考 `aic-coralreef` 的平台边界与服务拆分思路
- 先做前后端分离和服务边界清理，再做功能迁移

一句话概括：

- 这个项目真正该继承的是“业务能力”，不是“当前组织形态”。

