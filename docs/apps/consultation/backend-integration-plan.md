# `consultation` 前端接入后端与接口规范设计文档

## 1. 文档目的

这份文档不追求“一次性把前后端全部接完”，而是定义一条可分阶段执行、每一步都能单独验证的接入路线。

目标是：

- 保留当前原型页面的视觉效果与页面结构
- 让 `consultation` 浏览器端只访问 `gateway-service`
- 把当前“可浏览的原型页面”逐步切到“真实接口驱动页面”
- 在每一步都能快速定位问题，不把路由、UI、接口、状态一起混改

## 2. 当前代码现状

### 2.1 当前应用外壳

`apps/consultation` 目前已经是标准 app 外壳：

- `client/`：React + TypeScript + Vite 前端
- `server/`：FastAPI 静态托管壳
- 根 `Dockerfile`：构建前端并打包到 app server

其中 `server/app/main.py` 当前只负责：

- `/health/live`
- `/health/ready`
- `index.html`
- `/config.js`
- SPA 路由兜底

它不是业务后端，不承载认证、问诊、量表逻辑。

### 2.2 当前前端已经有一套真实 API 状态流

`client/src/app/useConsultationApp.ts` 已经实现了这些真实请求：

- `/auth/login`
- `/auth/register`
- `/auth/logout`
- `/users/me`
- `/users/me/profile`
- `/system/bootstrap`
- `/consultations`
- `/consultations/{id}`
- `/consultations/{id}/start`
- `/consultations/{id}/turns`
- `/assessment/catalog`
- `/assessment/sessions`
- `/assessment/sessions/{id}`
- `/assessment/sessions/{id}/answers`

并且还做了这几件很关键的事情：

- token 持久化
- consultation session id 持久化
- assessment session id 持久化
- 登录后 bootstrap 恢复
- 已有问诊会话 / 量表会话恢复

这说明“真实接口链路的骨架”其实已经在了。

### 2.3 当前页面仍主要跑的是原型 mock 链路

虽然顶层有真实 API 状态流，但页面本身并没有真正消费它。

当前仍然是：

- `HomePage` 只做本地路由跳转
- `PreparationPage` 使用本地 `useState` 和 `mockConsultationService.startConsultation`
- `ConsultationPage` 使用 `mockConsultationService.getState/sendMessage/getMultimodalData`
- `ScaleQuestionnairePage` 使用本地题库数组和 `mockConsultationService`
- `ResultPage` 与 `InterventionPage` 仍是纯展示页，数据基本写死

也就是说，现在存在两套并行链路：

1. `useConsultationApp.ts` 中的真实接口链路
2. 原型页面内部的 mock 页面链路

这正是当前最需要收口的问题。

### 2.4 当前路由真实行为

当前路由常量已经统一在 `client/src/routes.ts`。

现有受保护页面：

- `/home`
- `/preparation`
- `/consultation`
- `/scale-questionnaire`
- `/result`
- `/intervention`

当前登录后为什么会直接跳到问诊准备页：

- `resolveAppPath()` 把 `profile_status !== "completed"` 直接解析成 `/preparation`
- `App.tsx` 在登录成功后直接按 `resolvedPath` 跳转

所以现在的逻辑是“登录后恢复主流程位置”，不是“登录后先进入首页”。

### 2.5 问诊准备字段集直接统一

Step 3 不再保留“原型字段”和“目标字段”两套口径，前端页面、接口文档和接入设计统一只使用这一套字段：

- `full_name`
- `age`
- `gender`
- `height_cm`
- `weight_kg`
- `marital_status`
- `parents_marital_status`
- `parents_occupation`
- `prior_psychiatric_visit`

约定：

- `full_name` 更新顶层用户字段 `user.full_name`
- 其余字段进入 `user.profile`

## 3. 当前主要问题清单

### 3.1 流程入口不符合当前产品期望

当前产品期望是：

- 登录成功后先到首页

当前实际行为是：

- 登录成功后如果 `profile_status = draft`，直接进入问诊准备页

这不属于后端接口问题，而是前端流程编排规则问题。

### 3.2 页面层没有消费真实 API 状态

`useConsultationApp.ts` 已经有真实业务状态，但：

- `App.tsx` 只把认证动作传给了 `AuthPage`
- 其他页面没有接入 `state` 和 `actions`
- 页面内部仍然自己维护 mock 状态

### 3.3 页面组件里仍有大量写死信息

目前仍有：

- 硬编码的用户昵称
- 硬编码的头像
- 未接线的退出登录按钮
- 写死的评分和结论
- 写死的量表题目

### 3.4 域模型重复

当前存在两套类型体系：

- `client/src/types.ts`：真实 API 侧的 user / consultation / assessment
- `client/src/types/consultation.ts`：prototype mock 的 digital human / multimodal 数据

这不是错误，但如果后续不明确边界，就容易继续混用。

### 3.5 接口文档还缺两个实际被前端依赖的接口

当前前端已经依赖，但文档未正式列出的接口有：

- `GET /assessment/catalog`
- `GET /assessment/sessions/{id}`

如果不先补齐文档，后面很容易出现“代码能跑，但契约不清晰”的情况。

## 4. 接入总原则

### 4.1 浏览器只访问网关

浏览器端只能请求：

- `gateway-service`

不能直接请求：

- `identity-service`
- `consultation-service`
- `assessment-service`
- `risk-service`
- `multimodal-service`

### 4.2 保留原型 UI，替换数据驱动方式

本次接入的核心策略不是重写 UI，而是：

- 尽量保留原型页面结构
- 保留原型页面样式
- 仅替换内部状态来源、提交流程和跳转规则

### 4.3 每次只切一段链路

不一次性把全部页面一起改完，而是按阶段切：

1. 路由与登录落点
2. 首页和用户态
3. 问诊准备
4. 数字人问诊
5. 量表问诊
6. 结果与干预页

### 4.4 页面不直接散写请求逻辑

统一要求：

- 页面负责展示和交互
- API 调用集中到服务层 / hook 层
- 页面内部只保留纯 UI 局部状态

### 4.5 文档先于字段漂移

凡是接口字段、状态码、返回结构要变化，必须先改文档再改代码。

## 5. 目标流转规则

## 5.1 登录后的目标流

调整后目标：

1. 登录成功
2. 总是先进入 `/home`
3. 首页根据当前真实状态展示主 CTA
4. 用户点击 CTA 后进入对应阶段

推荐规则：

- 登录成功后固定跳 `/home`
- `HomePage` 根据当前业务状态决定 CTA 文案和下一跳

建议的 CTA 路由规则：

- `profile_status = draft`：CTA 跳 `/preparation`
- `profile_status = completed` 且没有 consultation：CTA 启动问诊并跳 `/consultation`
- consultation 进行中：CTA 跳 `/consultation`
- assessment 进行中：CTA 跳 `/scale-questionnaire`
- assessment 已完成：CTA 跳 `/result`

这样可以同时满足两个目标：

- 登录后先看到首页
- 首页仍然能恢复主流程

## 5.2 非登录态与恢复规则

推荐保留：

- 未登录访问受保护页面时跳 `/login`
- 浏览器刷新时按本地 token + session id 恢复 consultation / assessment
- 非法路由仍跳受保护态的“当前阶段”

需要区分两个概念：

- `postLoginPath`：登录成功后的固定落点，应为 `/home`
- `resumePath`：刷新、非法受保护路由、流程恢复时的真实阶段落点

当前代码里只有一个 `resolvedPath`，后续应拆成这两个语义。

## 6. 接口规范收口方案

### 6.1 前端 API 模块划分

建议把现有 `api.ts + useConsultationApp.ts` 中的请求逻辑拆成：

- `client/src/services/api/client.ts`
- `client/src/services/api/auth.api.ts`
- `client/src/services/api/user.api.ts`
- `client/src/services/api/bootstrap.api.ts`
- `client/src/services/api/consultation.api.ts`
- `client/src/services/api/assessment.api.ts`
- `client/src/services/api/contracts.ts`

其中：

- `client.ts`：统一 fetch、token、错误解析
- `*.api.ts`：按领域导出 typed 函数
- `contracts.ts`：统一请求和响应类型

### 6.2 状态组织建议

当前不建议马上引入新的状态库，先在现有 `useConsultationApp.ts` 上收口即可。

但需要明确拆分责任：

- `useConsultationApp.ts`：全局业务状态编排
- 页面组件：只负责展示
- 页面内局部 UI 状态：弹窗开关、展开收起、录音按钮动画、面板开关

### 6.3 类型分层建议

建议把类型分成两层：

- `client/src/types/api.ts`
  - `UserRecord`
  - `BootstrapPayload`
  - `ConsultationSession`
  - `AssessmentSession`
- `client/src/types/prototype.ts`
  - `MultimodalPanelData`
  - `DigitalHumanVisualState`

不要继续让 mock 视觉类型和后端领域类型混在同一个文件层级下。

### 6.4 返回包规范

前端继续假设网关返回统一包：

```json
{
  "code": 0,
  "data": {}
}
```

错误时统一按：

- HTTP 状态码
- `detail.message`
- `message`

三个层次解析。

### 6.5 本地持久化规范

当前已有三类本地持久化，应保留但收口：

- `mcs_session_token`
- `mcs_consultation_session:{userId}`
- `mcs_assessment_session:{userId}`

后续不要在页面组件里继续新增零散 localStorage key。

## 7. 分步骤实施方案

## Step 0：修正登录落点与路由语义

### 目标

先修正“登录后跳问诊准备页”的问题，让实际行为和产品要求一致。

### 需要做什么

- 在路由层区分 `postLoginPath` 与 `resumePath`
- 登录成功后固定跳 `/home`
- 刷新恢复和非法路由兜底仍按 `resumePath`
- `HomePage` 成为统一流程入口页

### 涉及文件

- `client/src/routes.ts`
- `client/src/App.tsx`
- `client/src/pages/HomePage.tsx`
- `client/src/app/useConsultationApp.ts`

### 验证方式

- 新用户登录后进入 `/home`
- 已完成用户登录后也先进入 `/home`
- 首页 CTA 能按状态继续流程

### 这一步为什么要单独做

因为它只改流程入口，不碰业务接口，不会把问题扩散到准备页和问诊页。

## Step 1：先收口 API 层，不改 UI

### 目标

把真实接口能力从 `useConsultationApp.ts` 中拆成可复用 API 模块，但暂时不切页面 UI。

### 需要做什么

- 抽出 `auth.api.ts`
- 抽出 `user.api.ts`
- 抽出 `consultation.api.ts`
- 抽出 `assessment.api.ts`
- 补充统一 contracts
- 保持现有 `useConsultationApp.ts` 只负责编排

### 额外文档动作

同步补齐接口文档中的两个缺口：

- `GET /assessment/catalog`
- `GET /assessment/sessions/{id}`

### 验证方式

- `npm run typecheck`
- 登录、退出、bootstrap 恢复行为不变

### 这一步为什么值得先做

因为后续每个页面接线都会依赖这些 API，如果 API 层不先收口，页面切到一半就会开始重复造轮子。

## Step 2：接通首页、顶栏、侧栏、账号态

### 目标

让 `/home` 真正成为真实用户态首页，而不是只负责静态跳转。

### 需要做什么

- `HomePage` 接入真实 `user / consultation / assessment` 状态
- 首页主按钮文案根据状态动态变化
- `Header` 使用真实用户名，不再写死“张三”
- `ProfileModal` 接入真实用户信息
- `ProfileModal` 的退出登录按钮接到 `handleLogout`
- `Sidebar` 的跳转不改，但高亮和禁用状态可以按阶段优化

### 涉及文件

- `client/src/pages/HomePage.tsx`
- `client/src/components/Header.tsx`
- `client/src/components/ProfileModal.tsx`
- `client/src/components/Sidebar.tsx`
- `client/src/App.tsx`

### 验证方式

- 登录后首页显示真实用户名
- 点击退出登录后返回登录页
- 首页 CTA 能根据真实状态跳不同页面

## Step 3：接通问诊准备页

### 目标

保留当前原型准备页 UI，但把准备信息提交改成真实接口。

### 这一页的唯一字段真源

- `full_name`
- `age`
- `gender`
- `height_cm`
- `weight_kg`
- `marital_status`
- `parents_marital_status`
- `parents_occupation`
- `prior_psychiatric_visit`

数据库清理约定：

- 旧版 `users.family_history` 属于准备页历史遗留字段，不再保留
- 通过 `identity-service` 迁移 `20260515_0003_drop_family_history_from_users.py` 删除
- 这里删除的是“用户基础档案旧字段”，不是问诊阶段里“家族史采集”这类症状筛查语义槽位

### 推荐做法

- 保留页面布局、卡片、弹窗和整体样式
- 直接把弹窗和摘要卡片收口到上面这 9 个字段
- `PUT /users/me/profile` 只接收这 9 个字段
- `full_name` 写入顶层用户字段，其余字段写入 `user.profile`
- `PUT /users/me/profile` 只能更新“当前登录会话对应的用户”，不允许前端传 `user_id`
- 数据归属和可见性由服务端按 session token 解析当前用户，不能依赖前端做用户隔离
- 设备授权、知情同意、医生风格选择这三块先继续保留在前端 UI 状态

### 提交流程

- 打开页面时从 `user.profile` 回填
- 保存时调用 `PUT /users/me/profile`
- 保存成功后更新 `user`、清空旧 consultation / assessment session id
- 保存成功后返回首页，或留在准备页提示“可开始问诊”

### 验证方式

- 草稿用户可进入准备页
- 表单能回填现有 profile
- 保存成功后刷新页面仍能看到已保存数据
- 使用 A 账号保存后，B 账号登录不能看到 A 的资料；重新登录 A 账号仍只能看到 A 自己的数据

## Step 4：接通数字人问诊页主链

### 目标

把数字人问诊页从“原型占位”推进到“真实会话、真实阶段、真实视频播放、真实多模态状态”的主链版本。

这一阶段已经超出“把问诊页接到 consultation 接口”这么简单，因此 Step 4 的细化设计单独收口在：

- [digital-human-consultation-step4-design.md](./digital-human-consultation-step4-design.md)

本节只保留实施摘要，详细接口、表结构、模型调用和多模态落库方案以那份文档为准。

### 需要做什么

- 页面不再读取 `location.state.sessionId`
- session id 由全局状态和本地持久化恢复
- “开始问诊”通过 `POST /consultations` + `POST /consultations/{id}/start`
- 问诊执行方式改成“固定视频播放清单 + 固定回答窗口”，V1 不做自动追问
- 顶部进度条改成真实四阶段：
  - `问候说明`
  - `主诉采集`
  - `症状筛查`
  - `风险筛查`
- 阶段一问候说明视频播放期间，后端异步完成多模态模型预热
- 阶段二到阶段四按“一段视频 -> 一次语音回答 -> 下一段视频”的顺序推进
- 每次回答都要保存：
  - 当前问题文本与视频元数据
  - 用户原始音频
  - ASR 转写文本
  - 语音情绪结果
  - 文本情绪结果
  - face / pose / EEG 的回答窗口聚合结果
- “刷新状态”通过 `GET /consultations/{id}`
- 页面根据返回状态处理：
  - `warming_up`
  - `playing_prompt`
  - `waiting_user_response`
  - `recording_response`
  - `processing_response`
  - `handoff_ready`
  - `paused_for_human_review`

### 暂时保留为前端占位的部分

- 高保真数字人口型驱动
- 自动追问
- 最终风险结论生成

但下面这些不再允许继续是假数据：

- 顶部四阶段进度
- 当前视频与当前问题字幕
- 用户回答转写字幕
- 多模态数据看板中的运行状态与最新结果

### 页面策略

- 中间主区域改为真实视频播放器，不再只是假数字人发光区
- greeting 视频播完后自动推进到下一阶段，不等待用户反馈
- 阶段二到阶段四在视频播完后开启回答窗口
- 用户回答优先走语音录制，不再把手动输入当成主入口
- `handoff_ready` 时由用户手动点击进入量表页
- `paused_for_human_review` 时进入高风险暂停展示态
- 右侧数据看板展示真实设备状态、模型预热状态和最新多模态结果

### 验证方式

- 能创建新会话并恢复同一会话
- 登录后重新进入问诊页时能恢复到正确阶段和正确题目
- 阶段一视频能自动播放并自动推进
- 阶段二到阶段四能按固定视频顺序逐题推进
- 每轮回答结束后能看到真实转写和真实多模态最新状态
- 原始音频、转写文本和多模态结果都能按当前用户、当前会话、当前题目正确绑定
- 阶段四完成后显示“进入量表问诊”入口

## Step 5：接通量表问诊页

### 目标

把当前本地题库换成真实 assessment session 数据。

### 需要做什么

- 用 `GET /assessment/catalog` 获取量表目录与展示文案
- 用 `POST /assessment/sessions` 创建量表会话
- 用 `GET /assessment/sessions/{id}` 恢复进度
- 用 `POST /assessment/sessions/{id}/answers` 提交当前答案
- 页面题目不再使用本地 `SCALE_QUESTIONS`
- 选项不再写死 A/B/C/D，而是读 `current_item.answer_options`

### 页面展示建议

- 顶部进度条由 `required_scales` / `selected_scales` 驱动
- 当前量表名来自 `assessmentCatalog` 与 `assessment.current_scale_slug`
- 当前题号来自 `assessment.current_item_index`
- 当前题目与选项来自 `assessment.current_item`

### 暂时保留为前端占位的部分

- 数字人视觉态
- 多模态右侧面板
- 语音反馈动画

### 验证方式

- handoff 后可以创建量表 session
- 刷新后能恢复未完成进度
- 提交一题后能进入下一题
- session 完成后跳 `/result`

## Step 6：接通结果页与干预页的最小真实数据版本

### 目标

先去掉硬编码假数据，让结果页展示真实聚合结果；干预页先保持原型 UI。

### 结果页建议

优先使用：

- `assessment.results`
- `assessment.aggregate_payload`

如果当前后端还没有完整 risk 结果接口，则结果页先展示：

- 已完成的量表列表
- 每个量表的得分
- 聚合摘要占位
- “完整临床决策结果待接入”提示

不要继续保留写死分数：

- `68/100`
- `中度抑郁`
- 固定 PHQ-9/SDS/SAS 分值

### 干预页建议

在 `intervention-service` 尚未接入前：

- 保留当前 UI
- 明确标识为“前端展示占位”
- 不写死带医学含义的个性化方案结论

### 验证方式

- 量表完成后结果页能显示真实 session 结果
- 刷新结果页不会丢失

## Step 7：清理 mock 残留与硬编码

### 目标

在主链都接通后，清理所有会误导排查的问题源。

### 需要清理的内容

- `client/src/services/consultationService.ts`
- `client/src/types/consultation.ts` 中只服务旧 mock 的内容
- `ProfileModal` 里的假用户
- `Header` 中的假用户名称
- `ResultPage` 里的固定评分
- `ScaleQuestionnairePage` 里的本地题库
- 所有为平滑迁移临时保留的兼容桥接逻辑
- 所有旧路由语义、旧状态分支、旧字段兼容写法
- 所有不再被主链使用的旧文件、空壳文件和过渡文件
- 兼容导出文件、事件桥接、临时 context/adapter 中已经失去价值的部分也要一起删除
- 例如：`client/src/api.ts` 这类兼容 re-export、`SHOW_PROFILE_MODAL_EVENT` 这类临时事件桥接，如果到最后已不再必要，也必须删除

### 清理顺序

必须在真实页面已经切过去后再删。

## 8. 逐步实施时的验收矩阵

| 步骤 | 主要目标 | 成功标志 |
| --- | --- | --- |
| Step 0 | 登录后先到首页 | 登录成功固定进入 `/home` |
| Step 1 | API 层收口 | 请求逻辑集中、类型通过 |
| Step 2 | 首页与账号态接通 | 真实用户信息、可退出登录 |
| Step 3 | 准备页接通 | profile 可回填、可保存、字段一致 |
| Step 4 | 问诊页接通 | consultation 会话可创建、恢复、推进 |
| Step 5 | 量表页接通 | assessment 会话可创建、恢复、逐题提交 |
| Step 6 | 结果页最小真实化 | 展示真实量表结果，不再写死假分数 |
| Step 7 | 清理 mock | 主链仅剩真实接口与必要前端占位 |

## 9. 推荐实施顺序

建议严格按下面顺序做，不建议跳步：

1. 先修登录落点
2. 再收 API 层
3. 再接首页与账号态
4. 再接问诊准备页
5. 再接数字人问诊页
6. 再接量表页
7. 最后处理结果页、干预页和 mock 清理

这样做的好处是：

- 每一步改动面小
- 每一步都能单独验证
- 出错时能迅速判断是路由问题、状态问题、字段问题还是接口问题

## 10. 当前建议结论

对这套 `consultation` 来说，最正确的策略不是“先把所有页面都接真接口”，而是：

- 先让首页成为唯一流程入口
- 先让 API 层成为唯一请求入口
- 再把各页面逐页从 mock 切到真实状态

当前代码基础已经足够做这件事，不需要推倒重来。

真正要做的是把已经存在的真实接口骨架和现在的原型页面壳接到一起，并且在接的过程中保持契约清晰、路由单一、状态单一。
