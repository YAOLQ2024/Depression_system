# 量表选择页接入设计

## 1. 背景

当前系统在数字人问诊完成后，会从问诊完成态直接创建 `assessment_session` 并进入量表作答页。

老师的新要求是：

- 在进入量表会话前新增一个“量表选择页”
- 用户可在当前活跃的 4 个量表中自行选择本次要做的量表
- 支持单选和多选
- 至少选择 1 个，不能 0 个直接进入
- 量表作答顺序仍按系统固定顺序执行，不支持用户拖拽改序
- 量表页顶部进度条只显示本次选中的量表
- 只要量表会话已经创建成功，后续就只能继续作答，不能回到选择页重选
- 结果页与后续风险计算接受“只做部分量表”的前提，不能再默认永远有 4 份结果

本设计先按“4 个量表全部可选、暂时没有硬性必做量表”落地，同时预留未来增加“必做量表”规则的接口与数据语义。

## 2. 本次范围

本次只覆盖当前 V1 活跃主链的 4 个量表：

- `phq9`
- `sds`
- `sas`
- `social-function`

明确不在本次范围内：

- `scl90`
- 量表排序自定义
- 量表说明/耗时走后端新接口
- 重做已创建的量表会话
- 调整量表评分规则本身

## 3. 当前现状

### 3.1 已有能力

- `assessment-service` 已支持：
  - 获取量表目录 `/assessment/catalog`
  - 创建量表会话 `/assessment/sessions`
  - 获取量表会话 `/assessment/sessions/{id}`
  - 提交量表答案 `/assessment/sessions/{id}/answers`
- 后端创建量表会话时，已经有 `selected_scales` 数据通道与 `assessment_sessions.selected_scales` 字段
- `assessment-service` 的推进逻辑已经按 `selected_scales` 切到下一份量表，不要求一定做满 4 份
- 前端量表页顶部进度条已经来自本地 `scaleSteps`，理论上可以改成按选中量表动态生成

### 3.2 当前缺口

- 问诊完成后没有“量表选择页”
- 前端 `createAssessmentSession` 的请求类型里还没有 `selected_scales`
- `useConsultationApp.handleStartAssessment()` 仍直接创建量表会话
- `ScaleQuestionnairePage.tsx` 当前的 `previewStages` 来自完整 catalog，默认会把所有活跃量表都做成进度步骤
- `workflow-resources/workflows/consultation-v1.yaml` 里的 `required_scales` 仍是 4 个量表全部写死，和“当前全部可选”的新口径不一致

## 4. 目标设计原则

- 只在现有量表链路前增加一个选择步骤，不重做量表作答主链
- 量表作答的真实执行序列以 `selected_scales` 为唯一事实来源
- 本期先不强依赖后端返回量表说明和预计耗时，前端静态配置兜底即可
- 选择页只负责“选哪些量表”，不负责决定做题顺序
- 一旦量表会话创建成功，后续恢复与继续逻辑全部沿用现有 `assessment_session` 恢复机制
- 结果页、历史页、聚合结果都必须接受“缺少未选量表结果是正常情况”

## 5. 目标用户流程

### 5.1 首次进入量表阶段

1. 用户完成数字人问诊，问诊状态进入 `handoff_ready`
2. 用户点击“进入量表评估”
3. 前端跳转到新增的量表选择页，而不是立即创建量表会话
4. 选择页展示 4 个活跃量表卡片
5. 用户勾选 1 个或多个量表
6. 用户点击“开始量表评估”
7. 前端调用创建量表会话接口，携带 `selected_scales`
8. 创建成功后持久化 `assessment_session_id`
9. 跳转到量表作答页

### 5.2 已创建量表会话后的恢复

1. 如果系统已经存在未完成的 `assessment_session`
2. 用户再次进入时直接恢复到量表作答页
3. 不再进入量表选择页
4. 也不允许重选量表

### 5.3 完成量表阶段

1. 量表会话按 `selected_scales` 逐份推进
2. 当最后一份选中的量表完成后，量表会话结束
3. 聚合结果只包含本次实际作答的量表
4. 结果页只展示本次实际作答的量表结果

## 6. 前端接入方案

### 6.1 新增页面与路由

新增页面：

- `apps/consultation/client/src/pages/AssessmentSelectionPage.tsx`

新增路由常量：

- `APP_PATHS.assessmentSelection = "/scale-selection"`

路由接入：

- `App.tsx` 注册 `AssessmentSelectionPage`

推荐的页面进入规则：

- `consultation.status === "handoff_ready"` 且 `state.assessment == null` 时，允许进入选择页
- `state.assessment != null` 且 `state.assessment.status !== "completed"` 时，进入选择页应直接重定向到量表作答页
- `consultation.status === "paused_for_human_review"` 时，不允许进入选择页

### 6.2 量表选择页展示数据

量表选择页的数据来源拆成两层：

1. 动态目录数据：来自 `/assessment/catalog`
2. 静态展示补充：前端本地配置

动态目录用于展示：

- `name`
- `short_name`
- `item_count`
- `timeframe`

前端静态配置用于展示：

- `description`
- `estimated_duration_text`

建议新增前端静态配置文件：

- `apps/consultation/client/src/features/assessment-selection/scaleSelectionMeta.ts`

建议结构：

```ts
export const ACTIVE_SCALE_SELECTION_ORDER = [
  "phq9",
  "sds",
  "sas",
  "social-function",
] as const;

export const SCALE_SELECTION_META = {
  phq9: {
    description: "...",
    estimatedDurationText: "约 2-3 分钟",
  },
  sds: {
    description: "...",
    estimatedDurationText: "约 4-5 分钟",
  },
  sas: {
    description: "...",
    estimatedDurationText: "约 4-5 分钟",
  },
  "social-function": {
    description: "...",
    estimatedDurationText: "约 2-3 分钟",
  },
} as const;
```

页面候选量表必须只展示当前 4 个活跃量表，不把 `scl90` 暴露给用户。

### 6.3 选择交互规则

- 支持单选和多选
- 至少选择 1 个
- 未选择时“开始量表评估”按钮禁用
- 卡片顺序固定为：
  - `phq9 -> sds -> sas -> social-function`
- 即使用户点击顺序不同，最终提交顺序也必须按系统固定顺序归一化

页面文案建议明确提示：

- “可多选”
- “本次至少选择 1 份量表”
- “系统将按固定顺序依次播报并作答”

### 6.4 从问诊完成页进入选择页

当前 `ConsultationPage.tsx` 中，问诊完成态按钮会触发 `handleEnd`，进而走 `handleStartAssessment()` 直接创建量表会话。

本次改为两段：

1. 问诊完成态按钮只负责跳转到选择页
2. 选择页点击确认后才调用 `handleStartAssessment(selectedScales)`

这样可以把“确认进入量表阶段”和“真正创建量表会话”分开。

### 6.5 `useConsultationApp` 调整

建议把：

- `handleStartAssessment()`

改成：

- `handleStartAssessment(selectedScales: string[])`

同时修改前端 API 类型：

```ts
export type CreateAssessmentSessionPayload = {
  encounter_session_id?: string | null;
  source_consultation_flow_run_id?: string | null;
  multimodal_session_id?: string | null;
  scale_handoff_payload?: Record<string, unknown>;
  selected_scales?: string[];
  required_scales?: string[];
};
```

创建时由选择页传入：

- `selected_scales`
- `required_scales: []`

如果用户在选择页返回上一页，只要量表会话尚未创建成功，就仍可再次进入选择页修改勾选。

### 6.6 顶部进度条按所选量表生成

`ScaleQuestionnairePage.tsx` 当前的 `previewStages` 来源于完整 catalog：

- `buildScaleAssessmentPreviewStages(state.assessmentCatalog)`

本次应改成：

1. 优先读取 `assessment.selected_scales`
2. 按 `selected_scales` 过滤 catalog
3. 按过滤后的量表重新生成 `previewStages`
4. 重新计算连续的 `stageOrder`

目标效果：

- 选了 1 个量表，顶部只显示 1 步
- 选了 2 个量表，顶部只显示 2 步
- 选了 4 个量表，顶部显示 4 步

建议新增一个按指定 slug 序列构建阶段的方法，例如：

```ts
buildScaleAssessmentPreviewStages(catalog, orderedSlugs)
```

或新增包装函数：

```ts
buildSelectedScalePreviewStages(catalog, selectedScales)
```

### 6.7 恢复路径与首页入口

建议同步调整：

- `resolveResumePath`
- `resolveHomeEntryPath`
- `resolveHomeEntryLabel`

规则建议：

- 有未完成 `assessment_session`：进入量表作答页
- 没有 `assessment_session`，但 `consultation.status === "handoff_ready"`：进入量表选择页
- 其它情况沿用现有逻辑

这样用户重新登录或从首页继续时，不需要再先回问诊完成页点一次按钮。

## 7. 后端与接口设计

### 7.1 可直接复用的现有接口

本次不需要新增“量表选择页专用后端接口”。

可直接复用：

- `GET /assessment/catalog`
- `POST /assessment/sessions`
- `GET /assessment/sessions/{id}`

也就是说，量表选择页本质上是现有 catalog + create session 的前端流程编排问题。

### 7.2 推荐补齐的创建会话入参

虽然 `assessment-service` 后端 schema 已经支持 `selected_scales`，但当前前端 contract 尚未声明。

此外，为了给未来“必做量表 + 可选量表并存”留出清晰语义，推荐在创建会话请求中补一个显式的 `required_scales` 字段。

推荐后端请求模型变更：

```py
class CreateAssessmentSessionRequest(BaseModel):
    user_id: str
    encounter_session_id: str | None = None
    source_consultation_flow_run_id: str | None = None
    multimodal_session_id: str | None = None
    scale_handoff_payload: dict[str, Any] = Field(default_factory=dict)
    selected_scales: list[str] = Field(default_factory=list)
    required_scales: list[str] = Field(default_factory=list)
    capture_context: dict[str, Any] = Field(default_factory=dict)
```

### 7.3 `required_scales` 与 `selected_scales` 的语义

本次必须明确两者语义：

- `required_scales`
  - 代表业务上被判定为“必须完成”的量表集合
  - 本期先允许为空
- `selected_scales`
  - 代表本次量表会话实际执行的量表顺序
  - 本期是作答流程、进度条、结果展示的唯一事实来源

当前阶段的业务口径是“4 个量表全部可选、没有硬性必做”，所以：

- `required_scales = []`
- `selected_scales = 用户选择结果`

### 7.4 `assessment-service` 创建逻辑建议

当前 `assessment_engine.create_assessment_session()` 里：

- `selected_scales` 已用于实际推进顺序
- 但 `required_scales` 还会优先取 `scale_handoff_payload.required_scales`

这会和当前“全可选”口径冲突。

建议改成：

1. 如果请求显式传了 `required_scales`，优先使用它
2. 否则再回退到 `scale_handoff_payload.required_scales`
3. 再否则回退为空数组

建议语义：

```py
effective_required_scales = normalize_required_scales(
    payload.required_scales,
    fallback=payload.scale_handoff_payload.get("required_scales") or [],
)
```

然后持久化：

- `session_record.required_scales = effective_required_scales`
- `session_record.selected_scales = selected_scales`

这样既能支持当前“无必做量表”的阶段，也能平滑过渡到后续“部分必做 + 部分可选”的规则。

### 7.5 对现有推进逻辑的影响

量表推进主链本身不需要重写。

因为当前推进逻辑已经按：

- `session_record.selected_scales`

决定下一份量表，所以只要 `selected_scales` 正确，以下能力都能天然复用：

- 当前量表切换
- 当前题定位
- 最后一份量表完成后自动结束
- 聚合结果只包含已完成的量表

## 8. 数据语义与兼容策略

### 8.1 与 `consultation-v1.yaml` 中 `required_scales` 的关系

当前 workflow 资源里，`scale-assessment.required_scales` 仍写着 4 个量表。

这在本期仍可以保留，原因是：

- 它继续表示“当前活跃量表候选池”
- 但不再直接等价于“本次用户必须完成的量表集合”

也就是说，本期要把“workflow 里的活跃候选量表”和“assessment session 里的真实必做量表”拆开理解。

本期的真实执行规则应当是：

- 活跃候选池：来自 workflow / active catalog
- 本次实际执行：来自 `selected_scales`
- 本次硬性必做：当前为空，未来再由 `required_scales` 承担

### 8.2 结果页与历史页兼容口径

从本期开始，前端所有“量表列表”类展示都必须遵循：

1. 优先使用 `assessment.selected_scales`
2. 只有在缺失时才回退 `required_scales`
3. 不能再默认固定显示 4 个量表

需要重点检查的前端区域：

- `ScaleQuestionnairePage.tsx` 顶部进度条
- `ResultPage` 中的量表结果分组与顺序
- 历史详情页中的量表摘要与回放

语义要求：

- 未选中的量表是“不参与本次会话”
- 不是“得分为 0”
- 也不是“结果缺失异常”

### 8.3 风险与聚合口径

本期风险与聚合必须接受部分量表结果：

- `aggregate_payload.scale_results` 只包含用户本次完成的量表
- `scale_count` 只统计本次实际完成的量表数
- 下游如果读取不到某份量表结果，应理解为“该量表未被选择”，而不是默认值

## 9. 页面结构建议

量表选择页建议包含以下区域：

1. 顶部标题区
   - 标题：量表选择
   - 副标题：请选择本次需要完成的量表，可单选或多选
2. 量表卡片区
   - 量表名称
   - 简短说明
   - 题目数量
   - 预计耗时
3. 规则提示区
   - 至少选择 1 个
   - 系统将按固定顺序依次进行
4. 底部操作区
   - 返回
   - 开始量表评估

如果后续引入必做量表，可直接在卡片上增加：

- “必做”标识
- 默认勾选且不可取消

本次先不实现这部分交互，只在设计上预留。

## 10. 推荐实施步骤

下面按建议顺序实施。每一步完成后都应可单独验证，避免前后端、路由、结果页一起混改。

## Step 1：先收口数据语义与创建会话 contract

### 目标

先把“本次实际做哪些量表”这件事在数据层讲清楚，避免后续页面做好了，但 `required_scales` / `selected_scales` 语义仍然混用。

### 改动内容

1. 前端 `CreateAssessmentSessionPayload` 增加：
   - `selected_scales`
   - `required_scales`
2. 后端 `CreateAssessmentSessionRequest` 增加：
   - `required_scales`
3. 调整 `assessment_engine.create_assessment_session()`：
   - `selected_scales` 继续作为实际执行序列
   - `required_scales` 优先取请求显式传入值
   - 当前量表全可选阶段，前端创建会话时传 `required_scales: []`
4. 保持现有量表推进逻辑不变，不在这一步改页面

### 完成标准

- 前端可以向 `POST /assessment/sessions` 发送 `selected_scales`
- 后端返回的 `assessment_session.selected_scales` 与提交值一致
- 当前阶段创建会话后，`required_scales` 为空数组，不再被 workflow 默认 4 个量表覆盖
- 不改前端页面时，也可以通过接口联调验证单选 / 多选会话能创建成功

## Step 2：新增量表选择页骨架与静态展示配置

### 目标

先把“量表选择页”作为独立页面立起来，并把只展示 4 个活跃量表、静态说明与预计耗时这件事做实。

### 改动内容

1. 新增：
   - `AssessmentSelectionPage.tsx`
   - `APP_PATHS.assessmentSelection`
   - 路由注册
2. 新增前端静态展示配置，例如：
   - `ACTIVE_SCALE_SELECTION_ORDER`
   - `SCALE_SELECTION_META`
3. 选择页只展示：
   - `phq9`
   - `sds`
   - `sas`
   - `social-function`
4. 页面先完成静态交互骨架：
   - 卡片列表
   - 勾选状态
   - “至少选 1 个”按钮禁用逻辑
   - 返回按钮
   - 开始按钮

### 完成标准

- 登录后在允许进入的条件下可以打开量表选择页
- 页面只显示 4 个活跃量表，不显示 `scl90`
- 每张卡片都有：
   - 名称
   - 简短说明
   - 题目数量
   - 预计耗时
- 未选中任何量表时，开始按钮不可点击

## Step 3：接通问诊完成页到选择页，再到量表会话创建

### 目标

把现有“问诊完成后直接创建量表会话”的链路拆成两段：

- 先进入选择页
- 再由选择页确认创建量表会话

### 改动内容

1. 调整 `ConsultationPage.tsx`：
   - 问诊完成态 CTA 改为跳转选择页
   - 不再在这里直接创建 `assessment_session`
2. 调整 `useConsultationApp.handleStartAssessment()`：
   - 改为接收 `selectedScales: string[]`
3. 选择页点击“开始量表评估”时：
   - 按固定顺序归一化选中的 slug
   - 调用创建量表会话接口
   - 成功后持久化 `assessment_session_id`
   - 跳转量表作答页

### 完成标准

- 从问诊完成页点击按钮会进入选择页，而不是直接进入量表页
- 在选择页单选任意 1 个量表后可以成功创建会话
- 多选时会按系统固定顺序创建 `selected_scales`
- 创建成功后页面跳转到量表作答页

## Step 4：让量表作答页的步骤与顺序完全受 `selected_scales` 驱动

### 目标

把当前量表页里仍默认“所有活跃量表都参与进度条”的逻辑收口掉，让进度条、阶段序号、预览阶段全部基于本次选择结果生成。

### 改动内容

1. 改造 `buildScaleAssessmentPreviewStages(...)`：
   - 支持按传入 slug 序列过滤 catalog
2. `ScaleQuestionnairePage.tsx` 改为：
   - 优先读取 `assessment.selected_scales`
   - 用它过滤 catalog 生成 `previewStages`
   - 重新计算连续 `stageOrder`
3. 检查当前量表定位逻辑：
   - `currentScaleSlug`
   - `currentStage`
   - `scaleSteps`
   - `ConsultationProgress`

### 完成标准

- 只选 1 个量表时，顶部进度条只显示 1 步
- 选 2 个量表时，顶部进度条只显示 2 步
- 当前高亮步骤与 `assessment.current_scale_slug` 一致
- 选 4 个量表时，页面行为与当前全量流程一致

## Step 5：收口恢复路径、首页入口与选择页准入规则

### 目标

确保“未创建会话时去选择页，已创建会话时去作答页”这条规则在刷新、重登、首页继续入口上全部一致。

### 改动内容

1. 更新：
   - `resolveResumePath`
   - `resolveHomeEntryPath`
   - `resolveHomeEntryLabel`
2. 选择页自身增加准入保护：
   - `consultation.status !== "handoff_ready"` 时不允许进入
   - 已存在未完成 `assessment_session` 时重定向到量表作答页
3. 保持现有恢复逻辑：
   - 已创建会话后只能继续，不能重选

### 完成标准

- 没有 `assessment_session` 且问诊已完成时，继续入口进入量表选择页
- 已有未完成 `assessment_session` 时，继续入口直接进入量表作答页
- 刷新页面后不会重新回到量表选择页
- 已创建会话后手动访问选择页会被重定向走

## Step 6：收口结果页、历史页与聚合展示口径

### 目标

把下游展示从“默认 4 个量表”改成“只展示本次选中的量表”，避免未选量表被误认为丢失或异常。

### 改动内容

1. 检查并更新结果页适配器：
   - 优先使用 `assessment.selected_scales`
   - 仅在缺失时回退 `required_scales`
2. 检查历史详情页与相关 adapter：
   - 量表顺序按 `selected_scales`
   - 未选量表不显示占位
3. 明确聚合解释口径：
   - 未选量表代表“不参与本次会话”
   - 不是“0 分”
   - 不是“结果缺失异常”

### 完成标准

- 结果页只显示本次选中的量表结果
- 历史详情页不会强行补出未选量表
- 聚合结果与风险展示能接受只返回部分量表结果

## Step 7：做联调验证与回归

### 目标

在主要链路都改完后，集中做一轮“选择页 -> 创建会话 -> 作答 -> 结果 -> 恢复”的回归，确保没有把现有量表主链打断。

### 改动内容

1. 验证单选场景
2. 验证多选场景
3. 验证全选场景
4. 验证刷新恢复
5. 验证重新登录恢复
6. 验证非法进入选择页的重定向
7. 验证结果页与历史页展示

### 完成标准

- 只选 1 个量表，做完后立即结束量表阶段
- 选 2 个量表，执行顺序固定，不受点击顺序影响
- 选 4 个量表时，与当前全量流程兼容
- 未选任何量表时不能创建会话
- 已创建会话后刷新页面，可直接恢复到量表作答页
- 已创建会话后再次进入，不出现量表选择页
- 结果页只展示本次选中的量表结果

## 11. 实施范围清单

### 11.1 前端

- 新增 `AssessmentSelectionPage.tsx`
- 新增 `APP_PATHS.assessmentSelection`
- `App.tsx` 注册新路由
- 新增量表静态展示配置
- `CreateAssessmentSessionPayload` 增加 `selected_scales` / `required_scales`
- `useConsultationApp.handleStartAssessment(selectedScales)`
- `ConsultationPage` 的完成态 CTA 改为跳选择页
- `ScaleQuestionnairePage` 改为按 `assessment.selected_scales` 生成步骤
- `resolveResumePath` / `resolveHomeEntryPath` / `resolveHomeEntryLabel` 更新

### 11.2 后端

- `CreateAssessmentSessionRequest` 增加 `required_scales`
- `assessment_engine.create_assessment_session()` 调整 `required_scales` 取值优先级
- 保持现有 `selected_scales` 推进逻辑不变

## 12. 结论

这次改造的核心不是重写量表主链，而是把“量表会话创建”前移拆成一个独立的选择步骤，并让 `selected_scales` 成为量表阶段真正的事实来源。

只要把下面 3 件事接好，主链就能比较平滑地完成切换：

- 在问诊完成和量表作答之间新增选择页
- 创建量表会话时显式传入 `selected_scales`
- 量表页、结果页、历史页统一按 `selected_scales` 驱动显示与聚合

这样既满足老师当前“用户自选量表”的要求，也为后续重新引入“必做量表”规则保留了清晰的扩展点。
