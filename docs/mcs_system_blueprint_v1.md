# MCS 系统蓝图与实施路线 V1

本文档是 `/home/ZR/data2/MCS` 的正式架构方案，替代此前面向 `Depression` 重构的蓝图。

本文档已根据老师确认的“主任务流图 + 子任务流图”修订。

适用前提已经变更：

1. 新项目根目录是 `/home/ZR/data2/MCS`，不是继续在 `Depression` 仓库里演化。
2. MCS 是全新项目，不保留旧系统兼容链路，不做 `/legacy/*`、旧网关代理、旧单体并行运行。
3. 产品主流程以老师确认的任务流图为准；[`流程.txt`](/home/ZR/data2/MCS/docs/流程.txt) 应视为该流图的文本版说明，并在后续保持同步。
4. [`交互剧本.txt`](/home/ZR/data2/MCS/docs/交互剧本.txt) 当前视为 V1 规则版剧本草案，后续允许继续迭代，但不能把剧本硬编码进业务逻辑。

---

## 1. 项目定位

MCS = `Multimodal Consultation System`

这是一个围绕“患者登录与问诊准备 -> 数字人交互问诊 -> 量表问诊 -> 临床决策 -> 调节干预 -> 对话回顾与再评估”的全新系统，不再以旧 `Depression` 项目的页面结构或路由结构为基础。

旧项目现在只剩两个价值：

- 提供可参考的已有能力和算法素材
- 提供可离线迁移的历史数据

旧项目没有以下地位：

- 不是 MCS 的运行时依赖
- 不是 MCS 的兼容后端
- 不是 MCS 的同仓共存目录

---

## 2. 固定业务主流程

当前必须围绕以下主流程设计系统，不允许再按旧系统的“SDS 页面 + 若干补丁模块”方式组织：

### 2.1 主流程

1. 患者登录
2. 问诊准备
3. 数字人交互问诊
4. 量表问诊
5. 临床决策
6. 调节干预
7. 对话回顾与再评估
8. 如需再次筛查，回到下一轮问诊准备，形成闭环

这条主链的含义必须固定：

- `患者登录` 只负责身份进入，不承载核心医疗流程。
- `问诊准备` 负责补齐/确认基础档案、设备状态、知情同意与交互说明确认，并由系统绑定默认数字人配置。
- `数字人交互问诊` 是第一段核心采集链路，不是普通聊天页。
- `量表问诊` 是第二段核心采集链路，包含量表选择与逐题作答。
- `临床决策` 才是把问诊结果、量表结果、多模态特征和规则整合为风险结论的阶段。
- `调节干预` 负责输出并执行个性化方案。
- `对话回顾与再评估` 负责沉淀历史、形成事件化记录、安排再评估并回流下一轮。

### 2.2 数字人交互问诊的固定拆分

根据老师确认的子任务流图，数字人交互问诊必须拆成以下四个子模块：

1. 初始问候与流程说明子模块
2. 主诉采集子模块
3. 症状筛查规则式问诊子模块
4. 高风险问题排查子模块

这四个子模块是产品级流程，不再沿用此前“基础信息 / 家庭背景 / 既往史 / 主诉”那种平铺式 stage 设计。

固定要求：

- 子模块 1 负责加载患者基础档案、系统绑定的数字人配置、开场说明、交互规则确认，并把系统切入正式问诊状态。
- 子模块 2 负责提出主诉问题、接收患者语音回答、转写并提取主诉关键词/主诉摘要。
- 子模块 3 负责根据主诉走规则式追问链，生成症状筛查结构化结果和下一步分支依据。
- 子模块 4 负责单独执行高风险问题排查，并在必要时触发高风险预警/人工介入分支。

V1 的规则：

- 先不上 LLM + RAG 主链
- 以规则树/状态机驱动问诊
- 患者回答必须同时保留原始输入、转写文本和结构化结果
- 症状筛查追问和高风险排查都必须处理三类分支：
  - 正常回答
  - 沉默无反馈
  - 答非所问 / 识别失败
- 高风险排查不是普通追问的一个问题，而是独立的安全门
- 如需采集家庭史、既往史等信息，应挂在“症状筛查规则式问诊子模块”的节点中，不再单独提升为产品一级 stage

### 2.3 量表问诊的固定拆分

根据老师确认的子任务流图，量表问诊必须拆成以下两个子模块：

1. 量表规则与选择子模块
2. 量表问诊子模块

量表规则与选择子模块负责：

- 读取量表配置规则
- 区分必做量表和可选量表
- 展示量表说明和作答说明
- 接收患者确认并进入作答状态

量表问诊子模块负责：

- 加载当前量表题目
- 题目展示与语音播报
- 接收患者作答
- 自动计分与进度更新
- 判断当前量表是否完成
- 完成后输出当前量表结果并进入下一量表或汇总阶段

### 2.4 量表阶段的固定要求

根据老师确认后的当前实施范围，量表阶段活跃主链固定为：

- PHQ-9
- SDS
- SAS
- 社会功能缺陷量表

补充说明：

- `SCL-90` 当前不进入活跃 V1 主链，只保留资源占位，后续如导师确认再单独恢复。

并且：

- 全程语音作答
- 每完成一个量表立即后端落库
- 前端不立即显示单量表结果
- 等全部必做/所选量表完成后再统一计算结果并展示
- 语音、表情、脑电、姿态等多模态信号仅作为辅助依据，不作为唯一判定依据
- 量表阶段必须同时保留量表得分、作答过程记录和多模态采集结果

### 2.5 临床决策、调节干预与再评估的固定链路

老师确认的主任务流图明确了量表之后的固定后链路：

1. 临床决策
2. 调节干预
3. 对话回顾与再评估

这三段的输入输出应当固定理解为：

- `临床决策`
  - 输入：问诊结果、量表得分、多模态特征、决策规则
  - 输出：风险等级/风险提示、就诊建议、生活建议、后续干预线索
- `调节干预`
  - 输入：方案库、干预策略规则、干预知识库、临床决策结果
  - 输出：个性化干预方案、执行记录、用户调节反馈
- `对话回顾与再评估`
  - 输入：问诊记录、量表记录、多模态记录、干预执行记录、执行反馈
  - 输出：历史追踪记录、再评估提醒、事件化随访信息、下一轮筛查入口

这决定了系统必须围绕“流程编排 + 分阶段提交 + 延迟聚合展示”来设计。

---

## 3. 架构总原则

### 3.1 MCS 是 greenfield，不做 runtime 兼容

MCS 的迁移策略不是“新系统包着旧系统跑”，而是：

- 从旧项目抽取可复用能力
- 在 MCS 中重新组织和重写
- 旧项目保留为参考源，不接入 MCS 运行链路

明确禁止：

- 在 MCS 中建立 `legacy/`
- 通过 API 代理旧 Flask
- 直接 import `Depression` 项目代码作为运行依赖
- 同时保留新旧两套页面和两套路由主链

### 3.2 先把流程编排当核心，而不是把页面当核心

MCS 的核心不是登录页、历史页、聊天页，而是“有状态的医疗式流程编排”。

因此系统设计重点必须放在：

- 流程状态机
- 规则问诊脚本
- 量表调度
- 多模态采集编排
- 风险分层计算
- 干预推荐与执行记录

### 3.3 剧本、量表、规则都必须配置化

`交互剧本.txt` 只是 V1 文本版本，正式实现时必须拆成机器可读资源：

- 流程定义
- 问诊节点
- 医生人设
- 分支处理规则
- 量表定义
- 风险规则
- 干预方案模板

不能继续把这些内容散落在：

- Python 视图函数
- HTML 模板
- 任意 `.txt`
- 临时脚本

---

## 4. 目标系统组成

建议 MCS 的顶层组织方式直接学习 `aic-coralreef`：

- `apps/`
- `services/`
- `packages/`
- `infra/`
- `docs/`

MCS 的特殊点，不是再把顶层展开得很复杂，而是在 `packages/` 里额外放一个承载流程资源的统一包。

## 4.1 前端应用

### 1. `consultation`

面向受试者/患者的主交互界面，负责：

- 患者登录后的问诊准备
- 问诊准备完成确认
- 数字人问诊
- 量表填写
- 临床决策结果展示
- 调节执行
- 对话回顾与再评估入口

### 2. `operations-console`

面向管理员/研究人员的后台，负责：

- 用户与权限管理
- 医生人设配置
- 剧本配置
- 量表配置
- 风险阈值配置
- 干预方案配置
- 记录查看与导出

## 4.2 后端服务

### 1. `gateway-service`

统一 API 入口，负责：

- 鉴权
- 请求路由
- SSE/流式转发
- 聚合接口
- 错误码统一

### 2. `identity-service`

负责：

- 用户注册/登录/退出
- 角色与权限
- 用户档案基础字段
- 会话状态

### 3. `consultation-service`

这是 MCS 的核心服务，负责：

- 问诊准备状态初始化
- 默认数字医生人设绑定与加载
- 初始问候与流程说明子模块
- 主诉采集子模块
- 症状筛查规则式问诊子模块
- 高风险问题排查子模块
- 问答转结构化记录
- 咨询会话生命周期
- 向量表阶段的流程移交

### 4. `assessment-service`

负责：

- 量表定义管理
- 必做/可选量表策略
- 量表选择子模块
- 量表作答会话
- 单量表提交与落库
- 全量表完成后的聚合计算

### 5. `multimodal-service`

负责：

- 语音转写接入
- 语音情绪/声学特征
- 表情识别
- 姿态识别
- 脑电接入适配
- 多模态结果标准化

### 6. `risk-service`

负责：

- 汇总问诊记录
- 汇总量表结果
- 汇总多模态特征
- 临床决策规则执行
- 风险分层计算
- 前端展示用风险结果生成

### 7. `intervention-service`

负责：

- 调节方式选择
- 调节内容生成/匹配
- 调节强度决策
- 执行内容记录
- 用户反馈接收

### 8. `followup-service`

负责：

- 对话回顾与事件化记录
- 记录追踪
- 再评估任务
- 历史查看
- 报告导出
- 闭环追踪状态

## 4.3 可选扩展服务

### `ai-service`

V1 不是主链必需，但保留扩展位：

- LLM 问诊增强
- RAG 知识增强
- 后续个性化追问
- 后续总结与智能推荐

注意：

- V1 规则版必须不依赖 `ai-service`
- 后续接入 LLM 时，也只能替换 `consultation-service` 内部引擎，不允许再长出第二条平行主链

## 4.4 最终规模口径

为了避免项目继续无节制扩张，MCS 的最终规模先固定为：

- `2` 个前端应用
  - `consultation`
  - `operations-console`
- `8` 个核心服务
  - `gateway-service`
  - `identity-service`
  - `consultation-service`
  - `assessment-service`
  - `multimodal-service`
  - `risk-service`
  - `intervention-service`
  - `followup-service`
- `1` 个可选扩展服务
  - `ai-service`

按 `aic-coralreef` 的部署方式估算，最终运行容器数控制为：

- 不启用 `ai-service` 时：`14` 个基础运行容器
- 启用 `ai-service` 时：`15` 个运行容器

基础运行容器的构成为：

- `1` 个入口代理容器：`nginx`
- `3` 个基础设施容器：`postgres`、`redis`、`minio`
- `2` 个应用容器：`consultation`、`operations-console`
- `8` 个核心服务容器

这条口径后续应保持稳定，不再随意新增第三个前端主应用或平行主链服务。

---

## 5. MCS 建议的顶层目录结构

`/home/ZR/data2/MCS` 顶层建议直接收敛为接近 `aic-coralreef` 的形式：

```text
MCS/
  README.md
  Makefile
  .editorconfig
  .gitignore
  .env.example

  apps/
    consultation/
    operations-console/

  services/
    gateway-service/
    identity-service/
    consultation-service/
    assessment-service/
    multimodal-service/
    risk-service/
    intervention-service/
    followup-service/
    ai-service/

  packages/
    core-lib/
    ui-kit/
    workflow-resources/

  infra/
    compose/
    nginx/
    scripts/
    env/
    monitoring/

  docs/
    architecture/
    api/
    adr/
    apps/
    operations/
    product/
    services/
    migration/
```

### 5.1 这样设计的原因

原因很简单：

- `aic-coralreef` 的顶层是收敛的，这点应该直接照学。
- 我上一版把“顶层分类”和“实现细节”混在一起了，所以看起来过于展开。
- MCS 真正需要额外强调的，只是流程/剧本/量表/规则这类运行时资源。
- 这些资源不需要再单独占一个顶层，而应该作为 `packages/workflow-resources` 来管理。

## 5.2 不允许出现的目录

在 MCS 根目录中，以下东西不允许出现：

- `new_features`
- `my_flask_app`
- `legacy`
- `resources`
- `data`
- `models`
- `research`
- `final_final`
- `临时`
- `各种备份`
- 零散 `.txt` 业务逻辑文件

## 5.3 文档目录与文档驱动开发规则

MCS 后续不应该再走“边想边写代码、细节散在聊天记录里”的方式。更合适的制度是：

1. 先锁定蓝图和 `packages/workflow-resources/` 的流程资源。
2. 再为当前要实现的 `app` / `service` 写详细设计文档。
3. 设计文档收口后，再进入代码实现。
4. 代码实现时如果设计发生变化，必须先回写对应文档。

`docs/` 建议直接和 `apps/`、`services/` 对齐：

```text
docs/
  architecture/
  operations/
  product/
  api/
  adr/
  apps/
    consultation/
    operations-console/
  services/
    gateway-service/
    identity-service/
    consultation-service/
    assessment-service/
    multimodal-service/
    risk-service/
    intervention-service/
    followup-service/
    ai-service/
```

每个 `app` / `service` 目录下，至少应先有：

- `overview.md`：职责边界、上下游依赖、非目标
- `api-and-data.md`：接口、事件、核心数据结构
- `flow.md`：本模块内部流程、状态流转、异常分支
- `tasks.md`：按阶段拆分的实现任务表

执行顺序上，不建议一开始就把所有远期模块都写成很细的空文档。更好的做法是：

1. 先把 `consultation`、`gateway-service`、`identity-service`、`consultation-service`、`assessment-service` 这批紧邻 Phase C / Phase D 的模块写细。
2. `multimodal-service`、`risk-service`、`intervention-service`、`followup-service` 先写职责边界和输入输出，再随着实现推进补细节。
3. `ai-service` 只保留扩展位文档，不提前写成一整套伪详细方案。

---

## 6. 最关键的新设计：workflow-resources 包

MCS 和旧项目最大的结构差异，是把“流程内容”提升为一等公民。

这些内容统一收进：

- `packages/workflow-resources/`

这样顶层仍然保持 `aic-coralreef` 风格，但流程资源也不会散掉。

## 6.1 `packages/workflow-resources/workflows/`

放整个产品级流程定义，例如：

```text
packages/workflow-resources/workflows/
  consultation-v1.yaml
  reassessment-v1.yaml
```

`consultation-v1.yaml` 应描述：

- 阶段顺序
- 阶段进入条件
- 阶段完成条件
- 阶段之间的状态传递
- 主任务阶段与子任务模块的映射关系

建议直接按老师确认的主链配置 stage id，例如：

- `patient-login`
- `consultation-preparation`
- `digital-human-consultation`
- `scale-assessment`
- `clinical-decision`
- `intervention-execution`
- `review-and-reassessment`

## 6.2 `packages/workflow-resources/doctor-personas/`

放系统内部的虚拟医生配置，例如：

```text
packages/workflow-resources/doctor-personas/
  doctor-a-calm-female.yaml
  doctor-b-formal-male.yaml
```

每个配置至少包含：

- 医生 ID
- 展示名称
- 头像/形象资源引用
- 声音配置
- 语气配置
- 适配剧本版本

注意：

- 这些配置由系统在问诊准备完成后自动绑定或按后台规则分配，不做患者前台选择页。

## 6.3 `packages/workflow-resources/interview-scripts/`

放规则版问诊脚本，不允许硬编码在 Python 中。

建议结构：

```text
packages/workflow-resources/interview-scripts/
  rule-v1/
    stage-01-greeting-and-briefing.yaml
    stage-02-chief-complaint.yaml
    stage-03-current-history-followup.yaml
    stage-04-high-risk-screening.yaml
    fallbacks.yaml
```

每个节点必须能描述：

- 机器人要说什么
- 期待什么输入
- 如何提取结构化字段
- 正常回答时去哪
- 沉默时去哪
- 识别失败时去哪
- 手动输入兜底如何触发

注意：

- 家庭史、既往史、社会关系等内容如果仍然需要采集，应作为 `stage-03-current-history-followup.yaml` 下的规则节点或字段提取规则，而不是单独再建一个产品一级 stage。
- 高风险排查脚本必须能触发“正常返回主流程”和“高风险告警/人工介入”两条不同后续链路。

## 6.4 `packages/workflow-resources/scales/`

放量表定义，不写死在后端代码里。

建议至少包括：

```text
packages/workflow-resources/scales/
  phq9.yaml
  sds.yaml
  sas.yaml
  social-function.yaml
  scl90.yaml
```

其中：

- `phq9.yaml`、`sds.yaml`、`sas.yaml`、`social-function.yaml` 属于当前活跃 V1 主链
- `scl90.yaml` 仅保留占位，不进入当前主流程

## 6.5 `packages/workflow-resources/risk-rules/`

放风险分层配置，例如：

- 阈值
- 权重
- 强制预警条件
- 问诊字段与量表字段的融合规则
- 高风险排查即时触发规则
- 临床决策输出映射规则

## 6.6 `packages/workflow-resources/intervention-programs/`

放调节方案模板，例如：

- 呼吸放松
- 舒缓音乐
- 视频/动画引导
- 图文卡片

每个方案包含：

- 适用条件
- 强度等级
- 执行资源
- 执行时长
- 执行后反馈问题

---

## 7. App 结构设计

这一层也应直接学习 `aic-coralreef/apps/*` 的统一外壳，而不是在 app 顶层堆大量子目录说明。

统一模板如下：

```text
apps/<app-name>/
  .gitattributes
  .gitignore
  Dockerfile
  README.md
  client/
  server/
```

也就是说：

- app 顶层只保留统一外壳
- `client/` 内部再组织页面和组件
- `server/` 内部只放 app 自己的轻量后端
- 业务主逻辑仍然统一进 `services/*`

## 7.1 `consultation`

建议技术栈：

- React
- TypeScript
- Vite
- Tailwind CSS
- Zustand 或 Redux Toolkit
- TanStack Query

app 外壳建议：

```text
apps/consultation/
  .gitattributes
  .gitignore
  Dockerfile
  README.md
  client/
  server/
```

`client/` 内部再细分：

```text
apps/consultation/client/
  package.json
  vite.config.ts
  tsconfig.json
  public/
  src/
    app/
    pages/
    features/
    shared/
```

这个前端不是普通 dashboard，而是一个强流程页面应用。

## 7.2 `operations-console`

同样采用统一外壳：

```text
apps/operations-console/
  .gitattributes
  .gitignore
  Dockerfile
  README.md
  client/
  server/
```

`client/` 内部再组织后台页面：

```text
apps/operations-console/client/
  package.json
  vite.config.ts
  src/
    pages/
      login/
      dashboard/
      users/
      doctor-personas/
      scripts/
      scales/
      risk-rules/
      intervention-programs/
      records/
      exports/
      settings/
```

---

## 8. 后端服务内部模板

这里也应该直接学习 `aic-coralreef/services/auth-service` 和 `apps/*/server` 的统一方式。

所有 Python 后端服务统一采用：

```text
services/<service-name>/
  README.md
  Dockerfile
  alembic.ini
  pyproject.toml
  requirements.txt
  .env.example
  seed.py

  alembic/
  scripts/
  tests/

  app/
    __init__.py
    main.py
    config.py
    database.py
    deps.py
    redis.py
    permissions.py
    api/
    models/
    schemas/
    services/
    clients/
    rules/
```

规则：

- 服务顶层结构必须统一，不允许每个服务自己发明目录制度
- `app/` 是唯一业务代码入口
- `api/` 放接口层
- `models/` 放 ORM 模型
- `schemas/` 放输入输出模型
- `services/` 放业务逻辑
- `clients/` 放跨服务调用
- `rules/` 放状态机、评分引擎、风控规则、剧本执行器

如果某个服务暂时不需要 `alembic`、`seed.py` 或 `scripts/`，可以先留空，但结构不改。

---

## 9. 各服务边界细化

## 9.1 `consultation-service`

必须内部拆成这几个子域：

- `doctor_catalog`
- `preparation_bootstrap`
- `session_state_machine`
- `greeting_briefing`
- `chief_complaint_capture`
- `history_followup_engine`
- `high_risk_screening`
- `script_engine`
- `response_parser`
- `handoff_to_assessment`

这里最重要的是 `script_engine`，它的输入不是硬编码字符串，而是 `packages/workflow-resources/interview-scripts/` 中的配置。

## 9.2 `assessment-service`

必须内部拆成：

- `scale_catalog`
- `scale_policy`
- `scale_selector`
- `scale_runner`
- `progress_tracker`
- `submission_engine`
- `aggregate_scoring`
- `assessment_session`

其中 `scale_policy` 负责处理：

- 哪些量表必做
- 哪些量表可选
- 哪些量表由虚拟医生推荐

## 9.3 `multimodal-service`

建议内部拆成：

- `capture_orchestrator`
- `asr_adapter`
- `speech_signal`
- `face_signal`
- `pose_signal`
- `eeg_adapter`
- `result_normalizer`

## 9.4 `risk-service`

内部拆成：

- `feature_assembler`
- `clinical_decision_engine`
- `risk_rules_engine`
- `risk_level_mapper`
- `front_display_mapper`

## 9.5 `intervention-service`

内部拆成：

- `plan_selector`
- `content_dispatcher`
- `intensity_policy`
- `execution_recorder`
- `feedback_receiver`

## 9.6 `followup-service`

内部拆成：

- `conversation_review`
- `event_builder`
- `timeline`
- `reassessment_scheduler`
- `report_builder`
- `exporter`

---

## 10. 数据与基础设施

## 10.1 数据库

MCS 统一使用 PostgreSQL，不再使用 SQLite。

推荐先使用一个 PostgreSQL 实例，多 schema 管理：

- `identity`
- `consultation`
- `assessment`
- `multimodal`
- `risk`
- `intervention`
- `followup`

## 10.2 Redis

用于：

- 登录态缓存
- 流程会话状态缓存
- SSE 流式通信辅助
- 异步任务状态

## 10.3 对象存储

音频、图像、姿态帧、脑电原始文件不要混在源码目录。

建议：

- 本地开发用 MinIO
- 数据库存引用
- 原始文件统一进入对象存储

## 10.4 容器化

必须上 Docker Compose，至少包括：

- `nginx`
- `consultation`
- `operations-console`
- `gateway-service`
- `identity-service`
- `consultation-service`
- `assessment-service`
- `multimodal-service`
- `risk-service`
- `intervention-service`
- `followup-service`
- `postgres`
- `redis`
- `minio`

`ai-service` 可作为可选服务单独启停。

---

## 11. 命名制度

### 11.1 顶层目录

- 统一小写英文
- 统一 `kebab-case`
- 只允许固定目录，不允许临时新增无分类目录

### 11.2 Python 文件

- `snake_case`
- 禁止无语义命名：
  - `test.py`
  - `tmp.py`
  - `111.py`
  - 中文文件名

### 11.3 前端文件

- 路由目录：`kebab-case`
- React 组件：`PascalCase.tsx`
- hooks：`use_xxx.ts` 或 `useXxx.ts` 选一种并固定
- API 文件：`xxx.api.ts`

### 11.4 资源文件

所有配置化资源使用 ASCII 文件名，例如：

- `consultation-v1.yaml`
- `stage-03-current-history-followup.yaml`
- `doctor-a-calm-female.yaml`

不允许：

- `最终版.txt`
- `新新新剧本.txt`
- `老师要的版本.docx`

---

## 12. 明确的“非兼容”规则

这部分必须写死，否则项目会再次失控。

1. MCS 不提供旧系统代理层。

2. MCS 不直接连接旧系统数据库。

3. MCS 不直接 import `Depression` 仓库中的 Python 模块。

4. 旧项目只能作为“人工参考源”或“一次性离线导入源”。

5. 如果要复用旧逻辑，必须以“复制后重构并补测试”的方式进入 MCS，而不是继续跨目录调用。

6. 后续如果流程变化，只改 `packages/workflow-resources/` 配置和对应服务引擎，不再额外开新链路。

一句话概括：

- MCS 只有一条主链，不能为了省事再养第二条。

---

## 13. 实施阶段

## Phase A：建 MCS 骨架和规则制度

目标：

- 把目录和制度先立起来

动作：

1. 在 `/home/ZR/data2/MCS` 建立固定目录骨架
2. 建立 `Makefile`
3. 建立 `infra/compose`
4. 建立 `packages/core-lib`、`packages/ui-kit`、`packages/workflow-resources`
5. 把 `流程.txt` 转成 `packages/workflow-resources/workflows/consultation-v1.yaml`
6. 把 `交互剧本.txt` 拆成 `packages/workflow-resources/interview-scripts/rule-v1/*.yaml`

验收：

- 目录结构固定
- 不再继续写散乱文本逻辑文件
- 流程与剧本开始配置化

## Phase B：先做壳层和身份

目标：

- 让 MCS 作为独立系统先跑起来

动作：

1. 搭建 `consultation`
2. 搭建 `operations-console`
3. 搭建 `gateway-service`
4. 搭建 `identity-service`
5. 打通登录、角色和问诊准备基础资料

验收：

- 新系统可独立登录
- 可进入问诊准备页并完成开始问诊前确认
- 完全不依赖 `Depression`

## Phase C：实现规则版数字人问诊主链

目标：

- 先把“问诊准备 -> 数字人交互问诊”做成产品主链

动作：

1. 实现 `consultation-service`
2. 建立问诊准备状态和正式问诊切换
3. 实现“初始问候与流程说明”子模块
4. 实现“主诉采集”子模块
5. 实现“症状筛查规则式问诊”子模块
6. 实现“高风险问题排查”子模块
7. 接入基础 ASR
8. 完成“正常/沉默/识别失败”三分支处理
9. 问诊结束后生成结构化问诊结果并移交量表阶段

验收：

- 用户可完整走完老师确认的四个问诊子模块
- 不需要 LLM 即可完成 V1 主链

## Phase D：实现量表与多模态阶段

目标：

- 把“量表问诊”阶段做实

动作：

1. 实现 `assessment-service`
2. 实现量表规则与选择子模块
3. 实现 `multimodal-service`
4. 实现量表问诊子模块
5. 先打通 `PHQ-9 / SDS / SAS / 社会功能缺陷量表` 四个活跃量表的单次落库和全量聚合
6. 打通语音、表情、姿态、脑电的标准化采集接口

验收：

- 完成量表主流程
- 单量表结果不提前展示
- 全量结束后统一产出聚合结果

## Phase E：实现临床决策与调节执行

目标：

- 把“临床决策 -> 调节干预”跑通

动作：

1. 实现 `risk-service`
2. 实现 `intervention-service`
3. 完成临床决策页和风险展示页
4. 完成干预内容执行页
5. 完成执行反馈回写

验收：

- 用户能拿到最终风险分层
- 用户能接收并执行调节建议

## Phase F：实现对话回顾、事件化记录与再评估

目标：

- 形成闭环

动作：

1. 实现 `followup-service`
2. 建立对话回顾与事件化记录
3. 建立历史时间线
4. 建立再评估计划
5. 建立导出与回访能力

验收：

- 系统具备“问诊—量表—决策—干预—再评估”闭环

## Phase G：可选接入 AI 增强

目标：

- 在不改变主链架构的前提下增强体验

动作：

1. 引入 `ai-service`
2. 在 `consultation-service` 内新增 `rule_engine` / `llm_engine` 抽象
3. 在固定流程不变前提下增加更智能追问能力

验收：

- AI 是增强项，不是另起炉灶的一条新系统

---

## 14. 当前最推荐的落地顺序

如果按优先级排序，我建议：

1. 先把 `MCS` 目录骨架按 `aic-coralreef` 风格搭起来。
2. 先把 `流程.txt` 和 `交互剧本.txt` 转成 `packages/workflow-resources` 下的结构化资源。
3. 先做 `consultation + gateway-service + identity-service + consultation-service`。
4. 然后做 `assessment-service + multimodal-service`。
5. 再做 `risk-service + intervention-service + followup-service`。
6. 最后再考虑 `ai-service`。

一句话总结：

- MCS 先做成一条干净的规则版主链，再在这条主链上做智能增强，不再走“旧系统拼补丁”的路。
