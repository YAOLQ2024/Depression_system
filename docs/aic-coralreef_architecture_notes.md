# aic-coralreef 项目架构学习笔记

更新时间：2026-04-23  
目标：沉淀 `aic-coralreef` 的实际架构、实现方式、部署方法和可复用经验，供后续重构 `/home/ZR/data2/Depression` 参考。

## 1. 一句话结论

`aic-coralreef` 不是传统“一个前端 + 一个后端”的项目，而是一个 **monorepo + 微前端 + 多后端服务 + 统一网关/BFF + 统一鉴权/RBAC + 统一应用目录 + 统一计量/配额 + Docker Compose 编排** 的平台型系统。

它最值得学习的地方不是某个页面，而是下面这套平台骨架：

- `Portal` 负责统一入口、登录、菜单、管理后台、MFE 容器。
- `Portal server (Express)` 负责 BFF/Gateway、动态路由、配额检查、身份头透传。
- `auth-service` 负责用户/组织/角色/JWT。
- `app-registry-service` 负责应用目录、租户订阅、用户可见性。
- `metering-service` 负责 AI 用量、配额、统计。
- 每个业务应用再各自拆成 `client + server`，前端通过 MFE 挂进 Portal，后端走统一网关接入。

这套思路非常适合拿来重构 `Depression` 这种“功能已存在但结构混乱、前后端未分离”的项目。

---

## 2. 技术栈总览

## 2.1 仓库与工程化

- Monorepo
- npm workspaces
- 根目录统一管理 `apps/*`、`packages/*`
- Node 版本在根 `package.json` 中要求 `22.22.0`

## 2.2 前端

- React
- Vite
- `@originjs/vite-plugin-federation`
- React Router
- Tailwind CSS
- Font Awesome / Lucide React
- Portal 里还用了 Redux Toolkit、Recharts

注意：

- 设计文档里有些地方还写 React 18，但实际代码里 Portal、部分业务应用已经是 React 19。
- 样式不是简单后台模板，而是走了比较明显的产品化 UI：渐变、卡片、深浅对比、局部动效、字体资源本地化。

## 2.3 后端

- 公共服务主要是 Python + FastAPI
- 业务应用后端也大量采用 Python + FastAPI
- Portal 的生产态网关/BFF 是 Node.js + Express
- 部分 AI 流程通过 Dify，部分应用直接走 OpenAI 兼容接口

## 2.4 数据与基础设施

- PostgreSQL
- Redis
- SQLAlchemy + Alembic
- Docker / Docker Compose
- Nginx 作为统一 HTTPS 入口

## 2.5 AI 相关

- Dify workflow/chatflow
- OpenAI 兼容接口
- 独立 `document-parser-service`
- `packages/core-lib` 中有 Dify/Metering 相关共享 SDK

---

## 3. 仓库结构是怎么分层的

核心目录职责非常清晰：

```text
aic-coralreef/
├── apps/                # Portal 与各业务应用
│   ├── portal/
│   ├── trans-expert/
│   ├── gmpclub/
│   ├── gmp-audit-master/
│   ├── gmp-investigator/
│   └── gmp-sop-expert/
├── services/            # 平台公共服务
│   ├── auth-service/
│   ├── app-registry-service/
│   ├── metering-service/
│   └── document-parser-service/
├── packages/
│   └── core-lib/        # 共享类型和 SDK
├── infra/               # docker compose / nginx / cert / init 脚本
├── ai/                  # Dify DSL、知识库脚本
└── docs/                # 设计文档
```

这个分层比“controller/service/model 全塞一个项目”高明很多，因为它直接把平台职责拆开了：

- 平台级功能进入 `services/`
- 业务域功能进入 `apps/`
- 复用代码进入 `packages/`
- 部署进入 `infra/`

对 `Depression` 重构时，最该抄的就是这个目录级拆分。

---

## 4. 系统是怎么搭建起来的

从 README 和 `infra/` 看，系统搭建顺序大致是：

1. 进入 `infra/`
2. 生成本地 HTTPS 证书
3. 复制 `.env.example` 为 `.env`
4. `docker compose build`
5. `docker compose up -d`
6. 运行 `init-db.sh`
7. 重启 Nginx
8. 统一从 `https://localhost:8443` 访问

### 4.1 核心基础设施服务

Compose 中统一编排了这些组件：

- `nginx`
- `portal`
- 各业务应用容器
- `postgres`
- `redis`
- `auth-service`
- `app-registry-service`
- `metering-service`
- `document-parser-service`

### 4.2 环境变量设计

`infra/.env.example` 已经把平台配置分类了：

- 端口
- JWT 密钥
- CORS
- Dify 地址/API Key
- OpenAI 兼容接口 Key/Base URL
- HuggingFace / Docling / GPU 开关
- 阿里云镜像仓库相关配置

这说明它不是“只在开发机上能跑”的随意项目，而是按可部署平台来设计的。

### 4.3 数据库初始化策略

`infra/init-db.sh` 会统一做两件事：

- 对各服务执行 Alembic migration
- 对 `auth-service` 与 `app-registry-service` 执行 seed

这意味着：

- 表结构不是手工 SQL 管理
- 初始用户、初始角色、初始应用目录都是自动化初始化

这对重构很关键。`Depression` 如果要长期维护，必须引入 migration 和 seed，不能继续靠手改数据库。

---

## 5. 它是怎么做前后端分离的

这里的“前后端分离”不是最普通的前后端分离，而是 **平台门户 + 微前端 + 每个业务应用独立后端**。

## 5.1 前端拆法

Portal 是宿主前端：

- 负责登录
- 负责主导航
- 负责全局管理后台
- 负责按用户权限展示可访问应用
- 负责动态加载业务子应用

每个业务应用前端是一个单独的 Vite 应用，例如：

- `apps/gmp-investigator/client`
- `apps/trans-expert/client`

它们通过 Module Federation 暴露：

- `name`
- `filename: remoteEntry.js`
- `exposes: { './App': './App.tsx' }`

Portal 再在运行时调用 `loadRemoteApp(remote_entry_url, scope, module)` 去加载远程模块。

## 5.2 后端拆法

每个业务应用一般也有独立 server，例如：

- `apps/gmp-investigator/server`
- `apps/trans-expert/server`

这些 server 负责：

- 自己的业务 API
- 自己的数据库表和 Alembic
- 自己的 AI 调用
- 自己的静态资源或 MFE 构建产物托管

## 5.3 API 入口并不直连业务服务

前端并不是直接把请求发到每个业务容器。

实际链路是：

`Browser -> Nginx -> Portal server(Express) -> auth/registry/metering/业务后端`

也就是说：

- 浏览器只看到统一域名
- 业务后端都藏在网关后面
- 认证、授权、配额、路由都在网关层处理

这就是典型的 **BFF/Gateway + 前后端分离**。

---

## 6. 微前端是怎么落地的

## 6.1 Portal 作为 Host

Portal 的 Vite 配置启用了 federation，并注册了 dummy remote 来初始化 shared scope。

Portal 前端中：

- 登录后请求 `/api/registry/discovery/apps`
- 得到当前用户可访问应用列表
- 列表里包含：
  - `id`
  - `name`
  - `remote_entry_url`
  - `backend_url`
  - `api_path_prefix`
  - `status`
  - `icon/logo/gradient`

然后根据 `remote_entry_url` 懒加载业务应用。

## 6.2 每个业务应用如何接入

业务应用要具备几样东西：

- 前端 `remoteEntry.js`
- 后端 API
- `aic-manifest.json`
- 在 registry 里有 app 记录

Manifest 一般描述：

- 应用 ID
- 名称
- 描述
- icon/logo
- `api_path_prefix`
- exposed module

Registry 还能通过 `/sync` 从业务应用后端拉取 manifest，同步元数据。

## 6.3 Nginx 如何处理 MFE 静态资源

Nginx 里为每个应用配了：

- `/apps/trans-expert/`
- `/apps/gmpclub/`
- `/apps/gmp-audit-master/`
- `/apps/gmp-investigator/`
- `/apps/gmp-sop-expert/`

这些请求直接转发到对应容器，用来取：

- `remoteEntry.js`
- `assets/*`
- logo/public 资源

而 `/api/*` 则不直接给业务应用，而是继续走 Portal server。

这个设计很聪明：

- 静态资源直出，简单
- API 统一治理，不散

---

## 7. 网关 / BFF 是怎么做的

这套系统的关键不是 Nginx，而是 `apps/portal/server/index.js` 里的 Express 网关。

## 7.1 Nginx 只做最外层入口

Nginx 主要负责：

- HTTP -> HTTPS 跳转
- TLS 证书
- MFE 静态资源转发
- 其他所有流量转到 `portal:3000`

所以 Nginx 更像入口反向代理，不承担复杂业务判断。

## 7.2 真正的网关逻辑在 Portal server

Portal server 做了这些关键动作：

- 代理 `/api/auth`、`/api/users`、`/api/orgs`、`/api/roles` 到 `auth-service`
- 代理 `/api/registry` 到 `app-registry-service`
- 代理 `/api/metering` 到 `metering-service`
- 其余 `/api/*` 动态转发到具体业务应用

## 7.3 动态路由是怎么做的

动态路由核心依赖两步：

1. 通过 `registry/discovery/apps` 取得当前用户可访问 app 列表
2. 用请求路径匹配 `api_path_prefix`

匹配不到时还有 fallback：

- `?serviceId=...`
- `Referer: /app/<appId>`

所以业务后端地址不是写死在前端里，而是通过 registry 元数据动态决定。

## 7.4 网关还承担了权限前置判断

在代理业务 API 之前，Portal server 还会做：

- 检查用户是否有这个 app 的访问权
- 检查 app 状态是不是 `maintenance` / `archived`
- 检查组织配额是否超限

只有通过这些检查，才会放行到业务后端。

## 7.5 身份透传方式

Portal server 会把当前用户信息注入请求头：

- `X-User-ID`
- `X-User-Email`
- `X-User-Name`
- `X-Org-ID`

后端业务应用优先信任这些头，而不是信任前端传的 userId/orgId。

这对重构 `Depression` 非常重要：

- 前端不要自己传“当前用户是谁”
- 网关统一注入身份
- 后端统一从 Header 或 Bearer Token 解析身份

---

## 8. 权限 / 鉴权 / 用户管理怎么做的

## 8.1 auth-service 的职责

`auth-service` 是整套平台的身份中心，负责：

- 登录
- 刷新 token
- 退出登录
- 用户 CRUD
- 组织 CRUD
- 角色 CRUD
- 角色分配
- 权限解析

## 8.2 数据模型

核心表：

- `users`
- `orgs`
- `roles`
- `user_roles`
- `user_profiles`
- `org_apps`（和应用订阅关联）

这说明它的权限模型不是拍脑袋，而是完整的：

- 用户属于组织
- 用户可被授予角色
- 角色带权限列表
- 角色又有层级

## 8.3 RBAC 模型

是一个典型的 3 层级 RBAC：

- System
- Org
- User

内置角色大概包括：

- `sys:admin`
- `sys:operator`
- `sys:viewer`
- `org:admin`
- `org:operator`
- `org:viewer`
- `user:member`

并支持角色继承，例如：

- `sys:admin -> org:admin -> user:member`

权限是落在 `roles.permissions` 里的 JSONB。

## 8.4 认证方式

认证是标准 JWT：

- 登录成功签发 `access_token`
- 还会签发 `refresh_token`
- Redis 里维护 token blacklist

密码存储使用 bcrypt。

## 8.5 鉴权方式

`auth-service` 自己会：

- 验证 Bearer Token
- 查用户状态
- 通过 `rbac_service` 展开角色继承
- 得到最终 permissions

然后在接口上通过依赖注入判断：

- `require_permission(...)`
- `require_any_permission(...)`

## 8.6 用户管理怎么落到前端

Portal 里有一整套管理页面：

- 用户管理 `UserManager`
- 角色管理 `RoleManager`
- 组织管理 `OrgManager`
- 应用管理 `AppManager`
- 用量管理 `UsageManager`
- 配额管理 `GlobalQuotaManager`

UI 侧通过 `UserContext.hasPermission()` 动态控制：

- 左侧导航显示哪些菜单
- 哪些路由能进入
- 哪些标签页能看见

这就是比较成熟的“前端展示权限 + 后端真实权限双保险”。

---

## 9. app-registry-service 是干什么的

这是整个平台很关键的一层，很多项目没有这层，结果就会越做越乱。

它负责三件事：

1. 全局应用目录
2. 组织订阅关系
3. 用户级访问覆盖

### 9.1 核心表

- `apps`
- `org_apps`
- `user_apps`

### 9.2 它解决了什么问题

- 哪些应用存在
- 每个组织买了/开通了哪些应用
- 某个用户是否被显式禁用某个应用
- Portal 首页应该展示哪些应用
- 动态代理应该把 `/api/xxx` 转发到哪里

### 9.3 Discovery 接口的价值

`/api/registry/discovery/apps`

这个接口本质上就是“给当前用户计算最终可见应用列表”。

Portal 只要调用这一个接口，就能同时拿到：

- 菜单来源
- MFE 远程地址
- API 前缀
- 应用状态
- 展示元信息

这比前端硬编码应用菜单高级很多，也更适合平台化扩展。

---

## 10. metering-service / 配额系统怎么做的

这个项目把 AI 用量单独拆成服务，这是很平台化的做法。

## 10.1 主要职责

- 接收各应用上报的 token/messages 消耗
- 存储 usage_records
- 管理 quotas
- 提供统计接口
- 提供 quota check 接口

## 10.2 数据模型

- `usage_records`
- `quotas`

维度包括：

- `org_id`
- `user_id`
- `app_id`
- token 数
- cost
- provider 类型

## 10.3 为什么它设计得比较好

它不是同步写 DB，而是：

1. 业务服务调用 `/api/metering/ingest`
2. 数据先写 Redis queue
3. 后台 worker 批量刷 PostgreSQL
4. 同时更新 Redis 中的 quota usage

这样做的好处：

- AI 主流程不被统计阻塞
- 高并发更稳
- 配额检查可以直接读 Redis，延迟很低

## 10.4 配额拦截发生在哪里

真正拦截发生在 Portal server 里：

- 代理业务请求前
- 先调用 metering `/quotas/check`
- 如果超限，直接返回 403

所以业务应用自己不用重复做一套 quota gate。

## 10.5 业务应用如何上报用量

两种常见方式：

- 业务后端直接用 Python service 调 metering
- 或使用 `packages/core-lib/MeteringClient`

像 `gmp-investigator` 的 AI service 就会在 LLM 调用完成后，把 usage 异步上报到 metering-service。

---

## 11. 业务应用模板是什么样

从 `gmp-investigator`、`trans-expert` 看，比较典型的业务应用模板是：

```text
apps/<app-name>/
├── client/          # React + Vite + Federation
├── server/          # FastAPI
├── Dockerfile       # 多阶段构建
└── metadata/manifest
```

## 11.1 前端职责

- 提供业务 UI
- 通过 `/api/<app-prefix>` 调接口
- 作为 MFE 被 Portal 加载

## 11.2 后端职责

- 处理业务 API
- 解析 `X-User-ID` / `X-Org-ID` / Bearer Token
- 访问数据库
- 调 LLM / Dify / parser service
- 上报用量
- 对外提供 `aic-manifest.json`
- 兼容直接托管 `remoteEntry.js` 和静态资源

## 11.3 一个重要实现细节

很多业务服务的 `main.py` 都同时承担：

- FastAPI API 入口
- `StaticFiles` 托管前端构建产物
- `/{full_path:path}` 的 SPA fallback

也就是说：一个业务容器既跑后端 API，也能给 Nginx 提供该应用的前端资源。

这个模式对中小团队很实用：

- 部署简单
- 边界清晰
- 不用再单独给每个 app 拆静态资源服务器

---

## 12. 网页设计是怎么做的

这个项目的 UI 不是视觉系统特别重，但足够稳定、统一、产品化。

### 12.1 Portal 的设计风格

- Tailwind 为主
- 大量卡片布局
- 深色侧边栏 + 浅色内容区
- 品牌色偏蓝/靛青/青色
- 应用卡片支持 gradient / icon / logo
- 登录页和弹窗都有明显的设计感

### 12.2 字体与资源策略

Portal 自带本地字体文件：

- Inter
- JetBrains Mono
- Plus Jakarta Sans

这意味着它没有完全依赖在线字体，部署更可控。

### 12.3 组件与权限结合

Portal 不是只做静态页面，而是把“权限”和“页面结构”绑定：

- 左侧导航按权限显示
- `/admin/*`、`/settings/*` 路由按权限守卫
- 无权限时直接 `Navigate` 回首页

### 12.4 业务应用也有自己的风格

例如 `gmp-investigator`：

- 有仪表盘、趋势图、知识库、工作流步骤页
- 有打印样式
- 有通知条、状态色、分阶段分析界面

说明这套架构既能做平台，也能承载复杂业务 UI。

---

## 13. 调试 / 开发 / 测试是怎么做的

## 13.1 前端本地开发

各 app 的 `client/vite.config.ts` 都配了 dev proxy，例如：

- `/api/gmp-investigator -> localhost:3005`
- `/api/trans-expert -> localhost:8001`

有些还支持开发态注入：

- `VITE_DEV_USER_ID`
- `VITE_DEV_ORG_ID`

方便本地绕过完整登录链路做联调。

## 13.2 后端调试

FastAPI 天然支持：

- `/docs`
- `/openapi.json`
- `/health`

这比传统 Flask/Express 手写调试接口方便很多。

## 13.3 专门的调试脚本

例如 `trans-expert/server/scripts/debug_workflow_response.py`：

- 直接打 Dify upstream
- 打印完整 JSON
- 输出字段路径
- 保存响应结果到文件

这非常适合调试 AI 工作流返回结构。

## 13.4 测试

项目里已经有不少 pytest 测试：

- `apps/gmp-audit-master/server/tests`
- `apps/gmpclub/server/tests`
- `apps/trans-expert/server/tests`
- `services/document-parser-service/tests`

测试重点包括：

- API
- 文档解析
- 历史记录
- metering payload
- 数据序列化

虽然不是全仓高覆盖，但至少说明作者有测试意识，不是纯手点页面开发。

---

## 14. 容器化是怎么做的

## 14.1 总体方式

统一用 Docker Compose 编排，所有服务进入同一个 bridge network。

## 14.2 业务应用容器模式

典型业务应用 Dockerfile 是两阶段：

1. `node` 阶段构建前端
2. `python` 阶段运行 FastAPI

把前端 `dist` 拷进后端容器一起提供。

这套模式的优点：

- 前后端构建流程清晰
- 运行态镜像比“一个 Node + 一个 Python 混一起”更干净
- 容器职责清楚

## 14.3 Portal 容器模式

Portal 也是两阶段：

1. Node 构建前端
2. Node 运行 Express server

因为 Portal 本身的生产态需要 Node 运行 BFF/Gateway，所以运行态还是 Node。

## 14.4 公共服务容器模式

`auth-service`、`app-registry-service`、`metering-service` 都是 Python 镜像直接运行 uvicorn。

## 14.5 文档解析服务

`document-parser-service` 更复杂，支持：

- CPU/GPU 分支
- 预下载模型
- 预构建 base image
- HuggingFace mirror

说明这套平台考虑过 AI 基础服务的重量级部署问题。

---

## 15. 这个项目最值得借鉴的架构点

如果是为重构 `Depression` 抽象经验，我认为最值得抄的是下面这些。

### 15.1 先做平台骨架，再搬业务

顺序应该是：

1. Portal/Host
2. Auth
3. Registry
4. Gateway/BFF
5. 业务应用 client/server

而不是先一头扎进业务页面重写。

### 15.2 让应用接入变成“注册”，不是“硬编码”

不要让 Portal 把 Depression 写死在菜单里。

应该让 Portal 只认：

- app id
- remote entry
- backend url
- api prefix
- manifest

以后要加新应用，改 registry 和 compose 即可。

### 15.3 身份必须由网关注入

这点非常关键。

重构 `Depression` 时不要再让前端自己传：

- 当前用户 ID
- 当前组织 ID
- 当前角色

这些都应该由统一网关在 JWT 校验后注入到 Header。

### 15.4 把“用户/组织/角色”从业务里抽出去

如果 `Depression` 未来不只一个系统或还会扩展别的应用，那用户管理必须平台化，不能埋在业务项目里。

### 15.5 把“业务逻辑”和“AI 调用”分层

从 `gmp-investigator` 可以看出：

- API router
- deps(identity)
- service(ai/metering)
- model/schema

分层比较清楚。

`Depression` 重构时也应至少拆成：

- API 层
- 领域服务层
- 外部 AI 适配层
- 数据层

### 15.6 尽早加 migration、seed、health、docs、tests

这几个东西很基础，但非常重要：

- Alembic migration
- seed 初始化
- `/health`
- `/docs`
- pytest

否则系统越重构越乱。

---

## 16. 如果把这套架构迁移到 Depression，建议怎么落

这里不是正式重构方案，只记录当前最合理的方向。

### 16.1 目标目录建议

```text
Depression/
├── apps/
│   ├── portal/
│   └── depression-core/
│       ├── client/
│       └── server/
├── services/
│   ├── auth-service/
│   ├── app-registry-service/
│   └── metering-service/      # 如果确实需要 AI 计量
├── packages/
│   └── core-lib/
├── infra/
└── docs/
```

### 16.2 第一阶段不要做太多业务创新

第一阶段最重要的是：

- 先把前后端拆开
- 先把登录/用户/权限抽离
- 先把旧 API 能跑起来
- 先把最关键页面接到新门户上

不要一开始就重写全部页面和全部逻辑。

### 16.3 Depression 未必一开始就需要完整 MFE

如果 `Depression` 当前只有一个业务应用，可以先做：

- 统一 Portal
- 一个业务 app：`depression-core`

MFE 机制保留，但先只挂一个 app。

这样之后再扩展成多应用不会推倒重来。

---

## 17. 当前项目里观察到的现实问题与注意点

这个项目整体架构是对的，但也不是完全没瑕疵。

### 17.1 文档与代码存在漂移

- 文档里部分技术栈版本偏旧
- 实际代码里 React 版本、应用实现方式已经有演进

所以学习时要以“代码为准、文档为辅”。

### 17.2 有些服务逻辑在重复写

例如：

- `app-registry-service`
- `metering-service`
- 某些业务服务

都各自实现了一遍 JWT 解析 / 角色展开 / identity helper。

这在规模继续增大时会变成维护成本。

对 `Depression` 来说，后续最好抽共享 auth helper/SDK，而不是每个服务复制一份。

### 17.3 存在迁移中的痕迹

例如 `gmpclub` README 明确说：

- FastAPI 新服务已接好
- 旧 Node proxy 仍临时保留

说明这个仓库本身也在持续重构，不是完全静态成品。

### 17.4 平台复杂度不低

这套架构的代价也很明确：

- 服务多
- 环境变量多
- 本地启动重
- 理解成本高

所以迁移到 `Depression` 时要控制节奏，不要一次性照搬全部复杂度。

---

## 18. 最后的判断

如果目标是把 `/home/ZR/data2/Depression` 从“结构乱、前后端没分离、难维护”重构成可持续演进的平台，那么 `aic-coralreef` 最值得学习的不是具体业务，而是这五个原则：

1. 平台能力和业务能力分开。
2. 前端 Host 与业务 MFE 分开。
3. 统一网关负责路由、权限、配额和身份透传。
4. 用户/组织/角色/应用目录单独服务化。
5. 每个业务应用都按照 `client + server + Dockerfile + migration` 的固定模板建设。

对 `Depression` 来说，最现实的路线不是“照抄所有服务”，而是：

1. 先抄目录和边界。
2. 再抄认证、网关、前后端分离。
3. 最后再决定要不要抄 registry、metering、document-parser 这些平台能力。

这样既能保留现有功能，又能逐步把项目从“狗屎结构”拉回到可维护状态。
