# Depression 重构蓝图与分阶段迁移路线 V1

> 说明：该文档基于“在 `Depression` 仓库内重构并分阶段迁移”的旧约束撰写。当前已被新的 [`mcs_system_blueprint_v1.md`](/home/ZR/data2/MCS/docs/mcs_system_blueprint_v1.md) 取代，后续以 MCS 全新项目方案为准。

本文档基于以下两份已有笔记综合形成：

- [`aic-coralreef_architecture_notes.md`](/home/ZR/data2/MCS/docs/aic-coralreef_architecture_notes.md)
- [`depression_current_state_and_refactor_baseline.md`](/home/ZR/data2/MCS/docs/depression_current_state_and_refactor_baseline.md)

目标不是“再写一份分析”，而是给 `Depression` 输出一版可以直接执行的重构方案，重点解决：

1. 未来系统长什么样。
2. 仓库和文件夹该怎么组织。
3. 网关、权限、鉴权、用户管理怎么落地。
4. 如何在保留现有功能的前提下逐步迁移，而不是一次性推倒重来。

---

## 1. 重构原则

### 1.1 学 `aic-coralreef` 的边界，不照抄它的技术选型

`aic-coralreef` 最值得借的是：

- 平台入口清晰
- 网关/BFF 清晰
- 公共服务和业务服务分开
- 前端与后端边界清晰
- 业务按模块拆，不往一个单体里乱堆
- 容器化和环境编排明确

但 `Depression` 不必硬抄它的 Node/Portal/MFE 细节。

对 `Depression` 更合适的做法是：

- 前端：单独 `portal-web`
- 后端：统一 `gateway-service` + 若干 Python FastAPI 业务服务
- 推理：保留 `multimodal-service` 和 LLM/RAG 适配层为独立服务
- 数据：从 SQLite 迁到 PostgreSQL
- 运行：Docker Compose 起步

### 1.2 先“分层和立规矩”，再“改业务代码”

这次重构最优先的不是“先把页面写漂亮”，而是先固定：

- 顶层目录分类
- 服务命名
- 模块边界
- API 命名
- 数据归属
- 鉴权方案
- 迁移顺序

如果这些不先定死，后面即使换了 React/FastAPI，也会重新长成一坨。

### 1.3 不做过度微服务

虽然参考 `aic-coralreef` 的服务化思路，但 `Depression` 当前团队规模和业务体量不适合一步拆成十几个服务。

V1 的目标是：

- 1 个前端应用
- 1 个网关/BFF
- 5 个核心后端服务
- 1 到 2 个推理/AI 适配服务

先做到“清晰可维护”，不是追求“服务越多越高级”。

---

## 2. 目标系统架构

## 2.1 目标部署单元

建议最终形成以下部署单元：

1. `portal-web`
   唯一 Web 前端，负责登录、工作台、量表、咨询、历史、管理页。

2. `gateway-service`
   统一 API 入口和 BFF，负责：
   - JWT/Cookie 校验
   - 前端会话管理
   - 请求聚合
   - SSE/流式转发
   - 旧系统兼容代理

3. `auth-service`
   负责：
   - 注册/登录/刷新令牌/退出
   - 用户资料
   - 角色与权限
   - 会话记录

4. `assessment-service`
   负责：
   - SDS/PHQ-9/GAD-7 等量表定义
   - 草稿、提交流程
   - 量表计分
   - 多模态提交元数据
   - 初步风险计算

5. `counseling-service`
   负责：
   - 聊天会话
   - 消息记录
   - Skill Router
   - Session Summary
   - 干预建议编排

6. `report-service`
   负责：
   - 工作台聚合数据
   - 历史记录
   - 详情报告
   - 趋势和时间线

7. `multimodal-service`
   负责：
   - 文本/语音/面部/姿态推理
   - EEG 适配入口预留

8. `ai-service`
   负责：
   - 对接本地 LLM
   - 对接 RAG
   - 联网搜索适配
   - Prompt/模型路由

### 2.2 为什么是这 8 个，而不是更多或更少

这是一个折中方案：

- 比当前 Flask 单体清晰很多
- 比完全细碎微服务更容易落地
- 能和当前 `new_features` 的模块边界基本对上

模块映射关系：

- `scale_assessment` -> `assessment-service`
- `risk_assessment` -> `assessment-service`
- `text_dialogue` -> `counseling-service`
- `intervention` -> `counseling-service`
- `session_summary_skill` -> `counseling-service`
- `skill_router` -> `counseling-service`
- `chat_intent_router` + `emollm_client` -> `ai-service`
- `multimodal_service` -> `multimodal-service`
- `main/history/detail` -> `report-service`
- `account` -> `auth-service`

### 2.3 请求链路

目标请求链路如下：

`Browser -> Nginx -> portal-web / gateway-service -> domain services`

更具体地说：

1. 浏览器只访问两个入口：
   - 前端静态资源：`portal-web`
   - API：`gateway-service`

2. `gateway-service` 只对浏览器暴露统一 `/api/v1/*`

3. 业务服务不直接对浏览器暴露，只对网关暴露

4. `gateway-service` 在迁移期间还承担一项特殊职责：
   - 把未迁移的旧 Flask 路由代理到 `legacy-monolith`

这相当于用“绞杀者模式”逐步替换旧系统，而不是一次性切换。

---

## 3. 建议的仓库顶层结构

新的仓库结构建议如下：

```text
Depression/
  README.md
  Makefile
  .editorconfig
  .gitignore
  .env.example

  apps/
    portal-web/

  services/
    gateway-service/
    auth-service/
    assessment-service/
    counseling-service/
    report-service/
    multimodal-service/
    ai-service/

  packages/
    api-contracts/
    shared-py/
    shared-ts/
    ui-kit/

  infra/
    compose/
    nginx/
    scripts/
    env/

  docs/
    architecture/
    api/
    adr/
    migration/
    operations/

  data/
    seeds/
    fixtures/
    migrations/

  models/
    multimodal/
    llm/

  external/
    emollm/
    reference-eeg-service/

  legacy/
    flask-monolith/

  research/
    experiments/
```

### 3.1 每个顶层目录的职责

- `apps/`
  只放最终面向用户的应用。当前只保留一个 `portal-web`。

- `services/`
  只放可部署后端服务。一个文件夹对应一个 deployable。

- `packages/`
  只放共享代码，不允许藏业务主逻辑。

- `infra/`
  只放部署、容器、Nginx、脚本、环境模板。

- `docs/`
  只放正式文档，不放临时聊天总结和随手记录。

- `data/`
  只放种子数据、fixtures、导入导出脚本和迁移产物。

- `models/`
  只放模型资产或模型引用说明，不允许和业务代码混放。

- `external/`
  只放“不是本系统核心代码，但运行上需要引用”的外部项目。

- `legacy/`
  只放待下线的旧系统。迁移完成后清空。

- `research/`
  只放实验性代码，默认不参与生产运行。

### 3.2 这个结构对当前仓库的映射

- 现在的 `Depression/depression/my_flask_app` -> `legacy/flask-monolith`
- 现在的 `Depression/depression/new_features` -> 按模块拆到 `services/*`
- 现在的 `Depression/depression/services/multimodal_service` -> `services/multimodal-service`
- 现在的 `Depression/EmoLLM` -> `external/emollm`
- 现在的 `Depression/reference_services` -> `external/reference-eeg-service`

---

## 4. 必须执行的命名制度

这部分要严格，不然目录再漂亮也会重新失控。

### 4.1 顶层目录命名

- 一律小写英文
- 一律使用 `kebab-case`
- 顶层只允许固定目录，不允许临时加散文件夹

允许：

- `services/gateway-service`
- `infra/scripts`
- `docs/migration`

禁止：

- `new_features2`
- `最终版`
- `test123`
- `各种备份`

### 4.2 Python 文件命名

- 业务模块文件使用 `snake_case`
- 只有服务入口允许叫 `main.py`
- 禁止再出现无意义文件名：
  - `test.py`
  - `111.html`
  - `串口.py`
  - `提示词.txt`

改成有语义的名字，例如：

- `scale_submission_api.py`
- `risk_rules.py`
- `chat_session_service.py`
- `prompt_counseling_system.md`

### 4.3 前端文件命名

- 页面目录：`kebab-case`
- React 组件：`PascalCase.tsx`
- hooks：`useXxx.ts`
- 前端 API 文件：`xxx.api.ts`

### 4.4 文档命名

正式文档一律放在 `docs/` 下，文件名使用 ASCII。

建议规则：

- 架构文档：`docs/architecture/<topic>.md`
- ADR：`docs/adr/ADR-0001-<topic>.md`
- 迁移文档：`docs/migration/<phase>.md`
- OpenAPI：`docs/api/<service-name>.openapi.yaml`

### 4.5 脚本命名

所有可执行脚本必须进入 `infra/scripts/`，并采用动词开头：

- `dev-up.sh`
- `dev-down.sh`
- `migrate-auth.sh`
- `seed-assessment.sh`

禁止把脚本散落在根目录和服务目录外层。

---

## 5. 各服务的内部目录模板

## 5.1 Python 服务统一模板

每个 Python 服务都使用同一套结构：

```text
services/<service-name>/
  README.md
  Dockerfile
  pyproject.toml
  .env.example
  alembic.ini

  migrations/

  src/
    app/
      main.py
      core/
        config.py
        logging.py
        security.py
      api/
        v1/
          router.py
          endpoints/
      domain/
        entities/
        services/
        policies/
      repositories/
      schemas/
      clients/
      tasks/

  tests/
    unit/
    integration/
```

规则：

- `api/` 只做输入输出和路由
- `domain/` 放业务规则
- `repositories/` 放数据库访问
- `clients/` 放跨服务调用
- `tasks/` 放异步任务

禁止：

- 在 `api/` 里直接写大量业务逻辑
- 在 `repositories/` 里写鉴权
- 在 `main.py` 里堆所有配置和初始化

### 5.2 前端统一模板

`portal-web` 建议使用：

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query

结构建议如下：

```text
apps/portal-web/
  README.md
  package.json
  tsconfig.json
  vite.config.ts
  .env.example
  Dockerfile

  public/
  src/
    app/
      router/
      providers/
      layouts/
    pages/
      login/
      dashboard/
      assessment/
      counseling/
      history/
      admin/
    features/
      auth/
      scale-assessment/
      risk-evaluation/
      counseling-chat/
      intervention-plan/
      reports/
    shared/
      api/
      ui/
      hooks/
      lib/
      types/
    assets/

  tests/
```

规则：

- `pages/` 只放路由页面
- `features/` 放业务能力模块
- `shared/` 放通用 UI 和工具
- 不允许把所有请求都堆在一个 `api.js`

---

## 6. API、网关、鉴权和用户管理方案

## 6.1 API 风格

不建议继续沿用现在那种过长的：

`/api/v1/<一级模块>/<二级能力>/<动作>`

因为实际落地会非常笨重，很多路径语义重复。

建议改成：

- 资源型接口优先
- 动作型接口只在必要时使用 `/actions/*`

示例：

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/users/me

GET    /api/v1/assessments/scales
GET    /api/v1/assessments/scales/{scale_code}
POST   /api/v1/assessments/submissions
GET    /api/v1/assessments/submissions/{submission_id}
POST   /api/v1/assessments/risk-evaluations

POST   /api/v1/counseling/sessions
GET    /api/v1/counseling/sessions/{session_id}
POST   /api/v1/counseling/sessions/{session_id}/messages
POST   /api/v1/counseling/sessions/{session_id}/summary
POST   /api/v1/counseling/interventions/actions/generate-plan

GET    /api/v1/reports/dashboard
GET    /api/v1/reports/history
GET    /api/v1/reports/{report_id}
```

### 6.2 统一响应格式

延续当前 `api_common.py` 的思路，但变成全服务统一标准：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_xxx",
  "timestamp": "2026-04-23T12:00:00+08:00"
}
```

同时统一：

- `health/live`
- `health/ready`
- `GET /api/v1/meta`

### 6.3 网关方案

`gateway-service` 负责：

- 接收前端请求
- 校验用户登录态
- 透传用户身份到后端服务
- 统一错误码
- 聚合多个服务的结果
- 代理 SSE 流式响应
- 在迁移期代理旧 Flask 路由

迁移期间建议保留一个特殊路由：

- `/legacy/*`

未完成迁移的页面或接口，先由网关转发到 `legacy/flask-monolith`，这样可以做到新旧并行。

### 6.4 鉴权方案

建议采用：

- 浏览器侧：HttpOnly Cookie
- 服务间：JWT access token
- 刷新机制：refresh token

浏览器流程：

1. 用户在 `portal-web` 登录
2. `gateway-service` 调用 `auth-service`
3. 登录成功后设置 HttpOnly Cookie
4. 后续前端只带 Cookie，不自己存 token

服务间流程：

- `gateway-service` 向下游传递经签发的 access token 或内部身份头
- 下游服务验证签名和权限声明

### 6.5 用户和权限模型

建议最小可行角色为：

- `admin`
- `researcher`
- `participant`

说明：

- `admin`：系统管理、用户管理、配置管理
- `researcher`：查看受试者数据、评估记录、研究分析
- `participant`：普通测评和咨询用户

核心表建议放在 `auth-service`：

- `users`
- `password_credentials`
- `roles`
- `permissions`
- `user_roles`
- `sessions`

不要再把整行 `userinfo` 直接塞进 session。

---

## 7. 数据与存储方案

### 7.1 主数据库

从 SQLite 升级到 PostgreSQL。

理由：

- 支撑多服务
- 支撑更可靠迁移
- 支撑索引和并发
- 支撑更规范的数据治理

### 7.2 数据归属

V1 不强求“每个服务一个 PostgreSQL 实例”，但必须做到：

- 一个 PostgreSQL 集群
- 每个服务独立 schema 或独立 database
- 不允许跨服务直接写表

推荐先用独立 schema：

- `auth`
- `assessment`
- `counseling`
- `reporting`

### 7.3 缓存与会话

引入 Redis，用于：

- refresh/session 状态
- SSE 流式会话辅助
- 短期缓存
- 异步任务状态

### 7.4 文件与原始媒体

音频、截图、EEG 原始数据不要再直接随手落在业务目录里。

统一进入：

- 本地开发：`data/fixtures/uploads/`
- 部署环境：MinIO 或对象存储

数据库只存元数据和引用地址。

---

## 8. 容器化、调试与运行制度

## 8.1 容器化基线

V1 必须上 Docker Compose，目录放在：

- `infra/compose/docker-compose.dev.yml`
- `infra/compose/docker-compose.prod.yml`

最少编排这些容器：

- `nginx`
- `portal-web`
- `gateway-service`
- `auth-service`
- `assessment-service`
- `counseling-service`
- `report-service`
- `multimodal-service`
- `ai-service`
- `postgres`
- `redis`

`external/emollm` 和 EEG 服务可先以外部依赖形式接入，不必立刻完全容器化。

### 8.2 本地开发命令

根目录统一通过 `Makefile` 暴露命令：

```text
make dev-up
make dev-down
make logs
make test
make lint
make migrate
make seed
```

所有底层脚本放在：

- `infra/scripts/`

### 8.3 调试制度

所有服务统一要求：

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/meta`
- stdout 结构化日志
- 每个请求带 `request_id`

不要再依赖“开一个脚本看看有没有报错”这种方式做系统级调试。

---

## 9. 分阶段迁移路线

这部分是整个方案最重要的部分。

## Phase 0：冻结旧系统并建立迁移基线

目标：

- 停止继续往 `my_flask_app` 和旧模板里加新功能
- 明确当前功能清单、数据库清单、接口清单
- 建立新仓库骨架

动作：

1. 把当前 `depression/my_flask_app` 标记为 `legacy/flask-monolith`
2. 把 `EmoLLM` 挪到 `external/emollm`
3. 把 `reference_services` 挪到 `external/reference-eeg-service`
4. 输出旧表清单和旧接口清单
5. 给现有功能做一版截图和行为基线

验收标准：

- 新目录结构已经建立
- 所有人停止向旧 Flask 单体新增功能
- 迁移期间所有新开发只进新结构

## Phase 1：先把“壳层”搭起来

目标：

- 让新系统先有入口，但不立即替换所有功能

动作：

1. 建立 `apps/portal-web`
2. 建立 `services/gateway-service`
3. 建立 `services/auth-service`
4. 建立 `infra/compose`、`infra/nginx`、`Makefile`
5. `gateway-service` 支持代理旧 Flask

这一步完成后，请求流变成：

`Browser -> portal-web / gateway-service -> legacy-monolith`

验收标准：

- 新前端能打开登录页和空工作台
- 网关能转发旧系统接口
- 登录后可通过网关访问旧功能

## Phase 2：优先迁移认证与用户域

目标：

- 先把最底层的登录、用户、权限从旧系统拿出来

动作：

1. 在 `auth-service` 重建：
   - 注册
   - 登录
   - 退出
   - 刷新令牌
   - 当前用户资料
2. 把 SQLite 的 `userinfo` 导入 PostgreSQL
3. 对密码做迁移：
   - 首次迁移时兼容旧密码
   - 用户首次成功登录后升级为安全哈希
4. `portal-web` 完成登录/登出/个人中心
5. 旧 Flask 页面改为信任网关透传身份，不再自己做长期演进

验收标准：

- 登录注册不再依赖旧 Flask
- 浏览器登录态只走新网关 + 新认证服务
- 旧系统在需要时可以被新身份透传访问

## Phase 3：迁移量表与风险评估

目标：

- 先迁最成熟、最稳定、最容易验证结果一致性的模块

动作：

1. 把 `new_features/scale_assessment` 拆进 `assessment-service`
2. 把 `risk_assessment` 并入 `assessment-service`
3. 重建这些 API：
   - 量表列表
   - 量表详情
   - 提交
   - 草稿
   - 最近一次结果
   - 风险评估
4. 把 `scale_assessment_records`、`scale_assessment_drafts`、旧 `test` 表中的相关数据迁到 PostgreSQL
5. 在 `portal-web` 完成：
   - 量表首页
   - 填写页
   - 结果页

验收标准：

- SDS/PHQ-9/GAD-7 新旧结果一致
- 风险评估逻辑输出与旧规则一致
- 用户无需再进入旧模板页就能完成量表主流程

## Phase 4：迁移咨询、总结和干预

目标：

- 把最复杂但最核心的咨询链迁出去

动作：

1. 把以下内容迁入 `counseling-service`：
   - `psychological_counseling.py`
   - `text_dialogue`
   - `intervention`
   - `session_summary_skill`
   - `skill_router`
2. 把以下内容迁入 `ai-service`：
   - `emollm_client.py`
   - `chat_intent_router`
   - LLM/RAG/Search 路由逻辑
3. `gateway-service` 打通 SSE/流式聊天
4. 重建 `portal-web` 咨询页

验收标准：

- 新咨询页可独立工作
- 会话总结可用
- 意图路由可用
- RAG/搜索/普通闲聊链路可分流

## Phase 5：迁移工作台、历史和报告

目标：

- 把“浏览和汇总层”从旧系统彻底拿出来

动作：

1. 在 `report-service` 重建：
   - 工作台数据聚合
   - 历史列表
   - 详情页
   - 趋势数据
2. 将 `main.py` 中剩余职责迁出
3. 建立新工作台和历史页面

验收标准：

- 登录后的主页面和历史页面不再依赖旧 Flask
- 旧系统只剩少量边缘功能或兼容接口

## Phase 6：迁移多模态与外部依赖整合

目标：

- 把“能独立的服务”彻底独立，把“外部项目”从主业务代码里摘干净

动作：

1. 保持 `multimodal-service` 独立部署
2. 给 EEG 做独立 adapter
3. 把所有多模态上传、任务状态、结果回传标准化
4. 明确 `external/emollm` 是外部依赖而不是业务代码

验收标准：

- 主业务系统不再和推理代码混目录
- 多模态链路只通过 API 调用

## Phase 7：下线旧单体

目标：

- 清理 `legacy/flask-monolith`

动作：

1. 逐个核对旧路由是否还有流量
2. 移除 `/legacy/*` 代理
3. 冻结并归档旧 SQLite 数据
4. 删除旧模板和旧视图逻辑

验收标准：

- 业务全量跑在新架构上
- `legacy/` 只剩归档，不再参与运行

---

## 10. 旧代码到新结构的映射表

### 10.1 认证和用户

- `my_flask_app/flask_app/views/account.py`
  -> `services/auth-service/src/app/api/v1/endpoints/auth.py`
  -> `services/auth-service/src/app/api/v1/endpoints/users.py`

### 10.2 量表和风险

- `new_features/scale_assessment/*`
  -> `services/assessment-service/src/app/domain/scale_assessment/*`

- `new_features/risk_assessment/*`
  -> `services/assessment-service/src/app/domain/risk_assessment/*`

- `my_flask_app/utils/scoring_system.py`
  -> `services/assessment-service/src/app/domain/legacy_sds/*`

### 10.3 咨询和干预

- `my_flask_app/flask_app/views/psychological_counseling.py`
  -> `services/counseling-service/src/app/api/v1/endpoints/counseling.py`

- `new_features/text_dialogue/*`
  -> `services/counseling-service/src/app/domain/text_dialogue/*`

- `new_features/intervention/*`
  -> `services/counseling-service/src/app/domain/intervention/*`

- `new_features/session_summary_skill/*`
  -> `services/counseling-service/src/app/domain/session_summary/*`

- `new_features/skill_router/*`
  -> `services/counseling-service/src/app/domain/skills/*`

### 10.4 AI 路由

- `my_flask_app/utils/emollm_client.py`
  -> `services/ai-service/src/app/domain/llm_router/*`

- `new_features/chat_intent_router/*`
  -> `services/ai-service/src/app/domain/intent_router/*`

### 10.5 历史和报告

- `my_flask_app/flask_app/views/main.py`
  -> `services/report-service/src/app/api/v1/endpoints/reports.py`
  -> `services/report-service/src/app/api/v1/endpoints/dashboard.py`

### 10.6 多模态

- `depression/services/multimodal_service/*`
  -> `services/multimodal-service/*`

---

## 11. 第一批必须制定的工程规则

为了防止新架构继续长歪，建议直接定这几条硬规则：

1. 不允许在根目录新增业务代码。

2. 不允许在 `legacy/` 中继续开发新功能。

3. 不允许业务服务直接访问别的服务数据库。

4. 不允许浏览器直接访问业务服务，只能走 `gateway-service`。

5. 不允许再出现中文代码文件名和无语义文件名。

6. 不允许把实验代码混进 `services/`，实验代码统一进 `research/`。

7. 不允许把模型文件混进业务源码目录。

8. 不允许把脚本散落在仓库各层，统一归 `infra/scripts/`。

---

## 12. 我建议的实际落地顺序

如果按“最低风险、最高收益”排序，建议先做下面四件事：

1. 先建立新仓库骨架和命名制度。

2. 先上 `portal-web + gateway-service + auth-service`，把入口和身份收口。

3. 第二批迁 `assessment-service`，因为量表和风险规则最稳定、最好验收。

4. 第三批迁 `counseling-service + ai-service`，这是复杂度最高的一块，放在入口和身份稳定之后做。

一句话概括整个迁移策略：

- 先搭壳层，再迁用户域，再迁稳定业务域，最后迁复杂 AI 域，再下线旧单体。
