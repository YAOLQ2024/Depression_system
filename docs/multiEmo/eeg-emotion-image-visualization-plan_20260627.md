# EEG 情绪面板图像化展示方案（非 Grad-CAM）

更新时间：2026-06-27

适用仓库：`depression-system`

适用范围：

- `apps/consultation/client`
- `services/multimodal-service`
- `docs/multiEmo`

---

## 1. 文档目标

本文用于明确 EEG 面板的新展示方向：

1. 不再使用 Grad-CAM 或任何“伪解释型热力图”方案。
2. 保留左侧 EEG 实时波形。
3. 将原右侧文字信息区改为纯图像化情绪展示区。
4. 将 EEG 分类结果压缩到“脑电情绪监测”标题行右侧展示。
5. 为后续正式改代码提供稳定的产品和工程边界。

本文只讨论展示方案与接入策略，不直接修改代码。

---

## 2. 决策结论

本次方案确定采用“纯图像情绪可视化”路线，不做 Grad-CAM。

原因如下：

1. 当前 EEG 模型是基于聚合特征向量的传统分类器，不是卷积特征图模型，不能自然产出标准 Grad-CAM。
2. 当前后端 live 数据只提供分类标签、主概率、Top3 概率和原始窗口索引，并不提供热力解释结果。
3. 当前产品目标更偏向“高可读、稳定、美观”的实时呈现，而不是科研解释可视化。

一句话定义本次方向：

**EEG 右侧区域改为“由分类概率驱动的三张情绪人脸图像展示”，而不是“由模型梯度驱动的解释热图”。**

---

## 3. 当前系统事实

## 3.1 当前 EEG 前端展示位置

当前 EEG 面板主要位于：

- `apps/consultation/client/src/components/ConsultationStatusPanel.tsx`

其中：

1. 左侧是 `EegWavePreview` 波形区域。
2. 右侧是“实时脑电 + 概率条 + Device + Latest Window”文字卡片。
3. 整块区域在咨询页和量表页都会复用。

受影响页面至少包括：

- `apps/consultation/client/src/pages/ConsultationPage.tsx`
- `apps/consultation/client/src/pages/ScaleQuestionnairePage.tsx`

## 3.2 当前 EEG 可直接使用的数据

当前前端类型中，已经具备本次图像方案需要的核心字段：

- `eeg_live.latest_result.primary_label`
- `eeg_live.latest_result.primary_score`
- `eeg_live.latest_result.top_3_labels`
- `eeg_live.device_status`
- `eeg_live.error_message`

其中 `top_3_labels` 已可直接映射为：

- 消极
- 中性
- 积极

因此，**P0 阶段不需要新增后端接口，即可完成标题摘要和图像驱动显示。**

## 3.3 当前 EEG 模型不适合 Grad-CAM

当前仓库中的 EEG 模型资产为：

- `services/multimodal-service/runtime-assets/eeg/EEG_model.pkl`

现状判断：

1. 主模型是基于 `scikit-learn` 的传统分类器链路。
2. 推理逻辑是“特征聚合 -> 标准化 -> 分类 -> 概率输出”。
3. 当前并不存在可直接用于 Grad-CAM 的卷积层特征图和梯度回传结果。

因此：

- 不建议把任何简单颜色蒙层命名为 Grad-CAM。
- 若后续需要“解释性可视化”，应单独走 SHAP / feature importance / channel saliency 路线，而不是沿用本方案。

## 3.4 当前前端不存在 3D 运行时栈

当前 `apps/consultation/client/package.json` 中没有：

- `three`
- `@react-three/fiber`
- `@react-three/drei`
- 现成的 `glb/gltf` 脸部模型资产

因此，当前最合理的路线不是引入实时 3D 引擎，而是：

**使用预渲染的 3D 风格人脸图片资源进行展示。**

这既符合“直接图像”的决策，也能显著降低前端复杂度与性能风险。

---

## 4. 目标 UI 方案

## 4.1 标题行改造目标

原目标：

- 右上角 `streaming`
- 右侧卡片中“实时脑电”
- `Device`
- `Latest Window`
- `状态采集中 · T7/T8/Fpz · 500Hz`

以上内容在新方案中全部移除，不再作为用户可见主信息。

标题行改为直接承载 EEG 分类摘要，例如：

```text
脑电情绪监测    中性·69%    消极24%；中性69%；积极7%
```

展示规则：

1. 第一段显示主分类与主概率。
2. 第二段显示三分类完整分布。
3. 不再显示设备采样率、通道名、窗口编号等工程信息。

颜色规则：

- 消极：蓝色字体
- 中性：黄色字体
- 积极：绿色字体

推荐色值：

- 消极：`#60a5fa`
- 中性：`#facc15`
- 积极：`#4ade80`

注意：

1. 主分类概率必须与三分类分布里的同类概率保持一致。
2. 不允许出现“主标签 90%，分布里同标签 80%”这类双口径冲突。

## 4.2 右侧图像区改造目标

原右侧文字卡片整体替换为“情绪图像显示区”。

建议采用三张图同时展示的方案：

1. 哭泣脸，对应消极，主色为蓝色。
2. 平静脸，对应中性，主色为黄色。
3. 高兴脸，对应积极，主色为绿色。

推荐布局：**纵向三联卡**

原因如下：

1. 当前 EEG 右侧区域本身较窄，纵向堆叠更适合现有版式。
2. 三张图同时展示，能直接表达三分类分布，不需要用户二次理解。
3. 后续若右侧宽度调整，也容易扩展为横向三联或主副卡布局。

每张图卡的显示元素建议包括：

1. 人脸主图。
2. 情绪标签角标，如“消极 / 中性 / 积极”。
3. 轻量百分比角标，显示该类当前概率。
4. 与情绪一致的边框光晕或背光。

## 4.3 图像强弱映射规则

三张图都显示，但强度不同。

建议映射如下：

1. 当前最高概率对应的人脸为“主激活态”。
2. 主激活态人脸具有更强亮度、饱和度、阴影和发光效果。
3. 其余两张图保留可见，但降低透明度和饱和度。
4. 当三类概率接近时，三张图都保持较高可见度，形成混合情绪感。

可映射的视觉参数：

- `opacity`
- `scale`
- `saturation`
- `glow strength`
- `border alpha`

推荐规则：

1. 主类：`opacity 100%`，`scale 1.00`，强发光。
2. 次类：`opacity 70%~85%`，`scale 0.96~0.98`，中等发光。
3. 最低类：`opacity 45%~65%`，`scale 0.94~0.96`，弱发光。

## 4.4 动效原则

新方案允许适度动效，但不应做成大型 3D 引擎动画。

推荐动效：

1. 结果切换时卡片光晕平滑过渡。
2. 概率变化时透明度与边框强度缓动。
3. 主状态切换时主卡片轻微放大。

不推荐：

1. 实时骨骼驱动表情。
2. 复杂 WebGL 3D 头模旋转。
3. 高频闪烁或强烈粒子特效。

目标是“稳定、克制、医疗场景可接受”，而不是娱乐化炫技。

---

## 5. 图像素材策略

## 5.1 P0 推荐方案

P0 采用三张预渲染 3D 风格人脸图。

建议资源形式：

- 透明背景 `webp` 或 `png`
- 建议 1:1 或接近 4:5 比例
- 建议最小分辨率 `1024 x 1024`

建议文件命名：

- `public/eeg-emotion/eeg-negative-crying.webp`
- `public/eeg-emotion/eeg-neutral-calm.webp`
- `public/eeg-emotion/eeg-positive-happy.webp`

## 5.2 素材要求

三张图的风格必须统一：

1. 同一人物脸型或同一套模型风格。
2. 同一光照方向。
3. 同一镜头距离。
4. 同一背景处理方式。
5. 同一渲染质感。

否则会导致：

- 三类切换像是三套不同系统拼接
- 界面气质不统一
- 情绪映射不可信

## 5.3 色彩原则

情绪与颜色关系固定：

- 消极 = 蓝色冷调
- 中性 = 黄色暖调
- 积极 = 绿色明调

这里的颜色应主要体现在：

1. 图像环境光或边缘辉光。
2. 卡片描边。
3. 标签文字和概率点缀。

不建议直接把整张人脸纯色染满，以免失真过重。

---

## 6. 数据映射方案

## 6.1 标题摘要映射

标题右侧内容来自：

- `latest_result.primary_label`
- `latest_result.primary_score`
- `latest_result.top_3_labels`

标准展示格式：

```text
主分类·主概率    消极x%；中性y%；积极z%
```

示例：

```text
中性·69%    消极24%；中性69%；积极7%
```

## 6.2 图像激活映射

三张图分别绑定固定标签：

| 图像 | 标签 | 主色 | 数据来源 |
| --- | --- | --- | --- |
| 哭泣脸 | 消极 | 蓝色 | `top_3_labels["消极"]` |
| 平静脸 | 中性 | 黄色 | `top_3_labels["中性"]` |
| 高兴脸 | 积极 | 绿色 | `top_3_labels["积极"]` |

每张图不做类别推断切换，只做强弱变化。

这样做的优点：

1. 视觉语义稳定。
2. 用户能快速形成“蓝-黄-绿”固定认知。
3. 不会出现图片突然替换导致跳变。

## 6.3 空状态映射

当 `latest_result` 不存在时：

1. 标题右侧显示“等待中”或空摘要占位。
2. 三张图全部降为低饱和、低亮度。
3. 不展示概率角标，避免误导。

推荐文案：

- `等待 EEG 分类结果`

## 6.4 异常状态映射

当设备未连接或推理失败时：

1. 不恢复旧的 Device / Window 说明块。
2. 标题右侧只显示简短状态，如“未连接”或“识别失败”。
3. 图像区整体置灰或降低亮度。

工程错误信息仍可保留在日志或调试模式中，不应进入主视觉区。

---

## 7. 前端实现建议

## 7.1 组件拆分建议

建议把当前 EEG 区域从一个大块中拆成更清晰的三个层次：

1. `EegHeaderSummary`
   - 负责标题右侧主分类与三分类摘要
2. `EegWavePreview`
   - 继续负责左侧波形
3. `EegEmotionImagePanel`
   - 负责右侧三张图像卡

图像区内部可再细分为：

1. `EmotionImageCard`
2. `EmotionProbabilityBadge`
3. `EmotionGlowFrame`

## 7.2 SectionCard 头部能力需扩展

当前卡片头部右侧只接受简单字符串状态。

若要承载：

- 主分类
- 主概率
- 三分类摘要
- 按类别着色文本

则建议将头部右侧从“纯文本状态”升级为“可插入自定义节点”的结构。

这将是本次前端改造的一个必要点。

## 7.3 性能建议

右侧图像区应只依赖 EEG 低频摘要结果，不应跟随波形高频样本一起重绘。

原因：

1. 波形是高频更新。
2. 分类结果是低频窗口级更新。
3. 图像区若绑定波形数组，会造成无意义重渲染。

因此，后续正式实现时建议：

1. 图像区只消费 `latest_result` / `top_3_labels`。
2. 波形区继续单独管理高频渲染。
3. 两者在组件层面尽量解耦。

这也与仓库中既有 EEG `summary / preview` 分流设计方向一致。

---

## 8. 后端改动边界

## 8.1 P0 阶段

P0 目标是完成新视觉方案，**默认不改后端接口**。

原因：

1. 现有 `latest_result` 已足够支持标题摘要。
2. 现有 `top_3_labels` 已足够驱动三张图像的强弱。
3. 现有 `primary_label` 与 `primary_score` 已足够决定主状态。

## 8.2 后端可选增强项

若后续要增强展示一致性，可考虑补充但非必须：

1. 保证 `top_3_labels` 始终包含消极 / 中性 / 积极三项。
2. 输出固定顺序的标准三分类字段。
3. 在 `latest_result` 中增加已经归一化好的三分类分布对象。

但这些属于体验优化，不是本次方案前置条件。

---

## 9. 分阶段落地建议

## Phase 1：纯前端结构替换

目标：

1. 移除右侧原有文字信息卡。
2. 标题行右侧显示主分类 + 三分类摘要。
3. 右侧改为三张情绪图像卡。

此阶段不新增后端字段。

## Phase 2：视觉细化

目标：

1. 为三张图补齐统一素材。
2. 加入轻量发光、透明度和切换动效。
3. 调整窄屏和不同分辨率下的排版稳定性。

## Phase 3：性能与结构整理

目标：

1. 将 EEG 标题摘要、波形、图像区彻底解耦。
2. 避免图像区跟随高频波形状态频繁更新。
3. 若需要，顺带清理当前 EEG 面板中过时的设备说明文案逻辑。

---

## 10. 风险与注意事项

## 10.1 最大风险不是“做不出图”，而是“图像语义不稳定”

如果三张图风格不统一，或者同一概率变化下表现不稳定，会导致：

1. 用户误解当前情绪状态。
2. 页面显得像拼贴素材，而不是系统化设计。
3. 图像展示比原始文字更难建立信任。

## 10.2 不要把纯视觉效果误写成算法解释

本方案中所有：

- 发光
- 明暗变化
- 颜色强弱
- 背景氛围

都只是 UI 映射效果，不应在文档、页面或汇报中称为：

- Grad-CAM
- 热力解释图
- 模型关注区域

## 10.3 标题摘要必须是唯一主口径

既然用户要求移除：

- 设备状态说明
- 采样率
- 通道名
- window-1

那么标题右侧摘要就成为 EEG 结果的唯一显式文字口径。

因此必须保证：

1. 展示稳定。
2. 分布完整。
3. 颜色固定。
4. 不出现双口径冲突。

---

## 11. 验收标准

满足以下条件可认为方案达成：

1. “脑电情绪监测”标题右侧直接显示主分类与三分类分布。
2. 原右侧“实时脑电 / Device / Latest Window”整块文本信息完全移除。
3. 右侧区域改为三张固定情绪图像展示。
4. 消极 / 中性 / 积极分别稳定映射为蓝 / 黄 / 绿。
5. 三张图能根据 EEG 分类分布表现出明显强弱差异。
6. 无 EEG 结果时有明确空状态，不误导用户。
7. 页面在咨询页和量表页中都能保持一致展示逻辑。

---

## 12. 默认实施假设

若后续没有新增产品指示，默认按以下假设推进：

1. 左侧 EEG 波形保留不动。
2. 标题右侧展示完整分类摘要。
3. 右侧图像区使用纵向三联卡。
4. 采用预渲染 3D 风格透明图片，而不引入实时 3D 引擎。
5. P0 不修改后端接口。

---

## 13. 一句话总结

本次 EEG 面板改造的核心不是“做解释性脑图”，而是把当前已有的三分类结果，稳定地转成一套更直观、更克制、更适合医疗场景的图像化情绪展示界面。

---

## 14. 组件级实施清单

本节把方案进一步细化到“改哪些文件、拆哪些组件、各组件分别负责什么”。

## 14.1 P0 预计涉及文件

P0 阶段建议优先改以下位置：

1. `apps/consultation/client/src/components/ConsultationStatusPanel.tsx`
2. `apps/consultation/client/public/eeg-emotion/*`

若希望减少 `ConsultationStatusPanel.tsx` 文件继续膨胀，建议额外新建：

1. `apps/consultation/client/src/components/eeg/EegEmotionImagePanel.tsx`
2. `apps/consultation/client/src/components/eeg/EmotionImageCard.tsx`
3. `apps/consultation/client/src/components/eeg/eegEmotionPresentation.ts`

其中：

- `eegEmotionPresentation.ts` 用于放标签常量、颜色映射、素材路径、概率归一化工具。
- 这样可以避免把 UI 常量继续塞回大组件。

## 14.2 `SectionCard` 需要的最小能力升级

当前 `SectionCard` 只有：

- `title`
- `rightStatus`
- `children`

这不足以承载新 EEG 标题头。

建议升级为以下能力之一：

### 方案 A：新增 `headerRight`

```ts
type SectionCardProps = {
  title: string;
  rightStatus?: string;
  headerRight?: ReactNode;
  hideStatusDot?: boolean;
  ...
}
```

使用原则：

1. 普通卡片继续走 `rightStatus`。
2. EEG 卡片传 `headerRight`。
3. EEG 卡片隐藏默认绿色状态点。

### 方案 B：直接拆成更通用头部插槽

```ts
type SectionCardProps = {
  header?: ReactNode;
  ...
}
```

P0 更推荐方案 A。

原因：

1. 改动范围更小。
2. 不会牵动其它卡片结构。
3. 更容易快速验证视觉效果。

## 14.3 EEG 标题头建议拆成独立组件

建议新增：

- `EegHeaderSummary`

建议 props：

```ts
type EegHeaderSummaryProps = {
  primaryLabel?: string | null;
  primaryScore?: number | null;
  distribution: Array<{ label: string; score: number }>;
  state?: "ready" | "pending" | "failed";
}
```

职责只包括：

1. 渲染主分类，例如 `中性·69%`
2. 渲染三分类摘要，例如 `消极24%；中性69%；积极7%`
3. 处理空状态或失败状态

不负责：

1. 设备状态
2. 波形数据
3. 图片显示

## 14.4 EEG 图像区建议拆成独立组件

建议新增：

- `EegEmotionImagePanel`

建议 props：

```ts
type EegEmotionImagePanelProps = {
  distribution: Array<{ label: string; score: number }>;
  primaryLabel?: string | null;
  hasResult: boolean;
  failed?: boolean;
}
```

职责：

1. 管理三张图的布局
2. 根据概率决定主激活态与次激活态
3. 处理空状态、失败状态、无结果状态

不负责：

1. 标题摘要
2. 波形
3. SSE 或数据获取

## 14.5 单张图卡建议拆为 `EmotionImageCard`

建议 props：

```ts
type EmotionImageCardProps = {
  label: "消极" | "中性" | "积极";
  score: number;
  imageSrc: string;
  accentColor: string;
  activeRank: 0 | 1 | 2;
  muted?: boolean;
}
```

职责：

1. 显示图片
2. 显示标签与百分比
3. 根据强弱切换透明度、发光、描边

## 14.6 EEG 数据转换工具建议单独收口

当前 `getEegDistribution()` 只做了基础排序。

P0 建议新增 3 个工具函数，放到单独文件或 `ConsultationStatusPanel.tsx` 局部底部：

1. `normalizeEegEmotionDistribution(result)`
   - 始终返回 `消极 / 中性 / 积极`
   - 缺失项补 `0`
2. `buildEegHeaderSummary(distribution, primaryLabel, primaryScore)`
   - 生成标题摘要所需结构
3. `resolveEmotionImagePresentation(distribution)`
   - 生成每张图的 `opacity / scale / glow / rank`

这样后续 UI 调整就不需要反复改 JSX。

## 14.7 `ConsultationStatusPanel` 中 EEG 区块的替换方式

现有 EEG 区块结构是：

1. `SectionCard`
2. 内层 `grid`
3. 左侧 `EegWavePreview`
4. 右侧文字卡

P0 替换建议：

1. 保留 `SectionCard`
2. 保留左侧 `EegWavePreview`
3. 将右侧文字卡整体替换为 `EegEmotionImagePanel`
4. 将原 `rightStatus` 改为 `headerRight={<EegHeaderSummary ... />}`

需要删除的可见内容：

1. `实时脑电`
2. `Device`
3. `Latest Window`
4. `状态采集中 · T7/T8/Fpz · 500Hz`
5. `window-1`
6. EEG 头部默认状态点与 `streaming/ready/pending` 文案

---

## 15. 样式级实施清单

本节只讨论视觉层，不讨论数据来源。

## 15.1 EEG 卡片头部样式建议

当前头部结构是单行 `justify-between`。

为了让“脑电情绪监测 + 右侧摘要”稳定显示，建议做以下调整：

1. 卡片头容器加 `gap-2` 和 `items-start`
2. 标题区域加 `min-w-0`
3. 右侧摘要区域加 `min-w-0 text-right`
4. 允许右侧摘要在窄宽度下自动换行

推荐类名方向：

```tsx
<div className="flex items-start justify-between gap-2 px-2 py-1.5">
  <h3 className="min-w-0 shrink-0 text-[13px] font-semibold tracking-wide text-slate-100">
    脑电情绪监测
  </h3>
  <div className="min-w-0 flex-1 text-right">
    ...
  </div>
</div>
```

摘要区建议分两层：

1. 第一层：主分类
2. 第二层：完整分布

推荐字号：

- 主分类：`text-[13px] font-semibold`
- 分布摘要：`text-[11px] leading-4`

## 15.2 标题摘要配色建议

主分类建议使用对应标签主色。

分布摘要建议逐段着色，而不是整句同色。

例如：

- `消极24%` 蓝色
- `中性69%` 黄色
- `积极7%` 绿色

推荐表现：

1. 文本本身有颜色
2. 分隔符 `；` 保持低饱和中性色
3. 不使用背景胶囊，避免标题区过重

## 15.3 EEG 内容区比例建议

当前内容区固定为：

- `h-[252px]`
- `grid-cols-[1.82fr_0.98fr]`

这个比例对于“三张纵向图卡”偏紧，但仍可作为 P0 起点。

推荐调整方向：

### 方案 A：保留现有比例

优点：

1. 不影响现有波形主视觉地位
2. 改动小

风险：

1. 右侧三张图高度会比较紧
2. 每张图只能做很轻量的信息

### 方案 B：微调为更利于图像展示的比例

建议尝试：

- `grid-cols-[1.68fr_1.12fr]`

这样右侧可多拿到一些宽度和高度感知空间。

P0 建议先从方案 B 试起。

## 15.4 `EegEmotionImagePanel` 布局建议

推荐结构：

```tsx
<div className="grid h-full grid-rows-3 gap-2">
  <EmotionImageCard ... />
  <EmotionImageCard ... />
  <EmotionImageCard ... />
</div>
```

每张图卡建议样式：

```tsx
<div className="relative overflow-hidden rounded-[14px] border border-white/10 bg-white/[0.04]">
  ...
</div>
```

图卡内部建议包含 4 层：

1. 背景底色层
2. 人脸图像层
3. 渐变遮罩层
4. 标签与百分比层

## 15.5 单张图卡的建议样式细节

建议基础结构：

```tsx
<div className="relative h-full overflow-hidden rounded-[14px] border">
  <img className="absolute inset-0 h-full w-full object-cover" />
  <div className="absolute inset-0 bg-gradient-to-r ..." />
  <div className="absolute inset-x-0 bottom-0 p-2" />
</div>
```

建议视觉参数：

1. 图像使用 `object-cover`
2. 图像亮度随概率变化
3. 激活态加 `shadow-[0_0_24px_rgba(...)]`
4. 非激活态降低 `saturate` 与 `opacity`

标签区建议：

1. 左下角显示标签
2. 右下角显示百分比
3. 标签和数值用白字或近白字
4. 再用对应情绪色做一层细描边或光晕

## 15.6 空状态样式建议

无结果时不要让右侧完全空白。

推荐表现：

1. 三张图保留轮廓
2. 图片整体灰化
3. 标签保留
4. 百分比隐藏
5. 区域中央或顶部可有一句极轻提示

推荐提示文案：

- `等待 EEG 分类结果`

## 15.7 失败状态样式建议

失败态与空状态要区分。

推荐：

1. 失败态整体偏冷灰
2. 右上或中部出现简短失败提示
3. 不展示旧的成功分类颜色

推荐文案：

- `识别失败`
- `设备未连接`

## 15.8 动效建议

推荐只做如下轻量动效：

1. `transition-all duration-300`
2. 激活态 `scale-[1.01]`
3. 光晕透明度平滑变化
4. 概率数字淡入更新

不建议：

1. 连续脉冲特效
2. 粒子外发光
3. 高频缩放跳动

## 15.9 响应式建议

当前面板容器宽度为：

- `w-[45vw] max-w-[650px]`

因此在较窄屏幕上，标题摘要可能放不下整行。

建议规则：

1. 宽度充足时，标题与摘要同一行显示
2. 宽度不足时，摘要允许换成两行
3. 不要强行压缩到单行省略号

原因：

1. 三分类分布是核心信息
2. 被截断后会损失关键含义

---

## 16. 问题确认结果

下面是基于当前代码结构，我已经确认的“真实问题”。

## 16.1 已确认存在的问题

1. 当前 `SectionCard` 头部 API 不够用，无法直接承载彩色分类摘要。
2. 当前 EEG 卡片头部默认带绿色状态点和 `streaming/ready/pending` 文案，这和新需求冲突。
3. 当前 EEG 右侧区是固定窄列，直接塞三张图会偏拥挤，需要同步微调列比例或卡片密度。
4. 当前右侧区域里的 `Device / Latest Window` 删除后，失败态和未连接态需要新的轻量替代表达，否则状态不可感知。
5. 当前仓库没有现成的 EEG 情绪人脸图素材，也没有 3D 运行时资源，素材需补充。
6. 当前咨询页和量表页都复用同一个 `ConsultationStatusPanel`，所以实现不能只针对单页写死。
7. 当前 EEG 概率分布虽然基本够用，但前端仍应做固定三类归一化，避免某一类缺失时摘要展示不完整。

## 16.2 已确认但不阻塞 P0 的结构问题

1. 咨询页里的 EEG 实时流订阅仍和侧边面板展开状态绑定，不是页面级绑定。
2. 当前 EEG 高低频状态仍在同一套页面状态里合流，不是完全解耦。
3. 这些问题不会阻止本次图像化改造，但会影响后续做更复杂动效时的稳定性与性能。

## 16.3 当前方案本身没有原则性问题

在“不做 Grad-CAM、先走纯图像方案”的前提下，当前方案本身没有原则性错误。

也就是说：

1. 数据口径是闭合的。
2. UI 表达目标是明确的。
3. P0 不依赖后端改造。
4. 主要工作量集中在前端结构调整、素材接入和样式实现。

---

## 17. 建议的正式开发顺序

若下一步开始真正动代码，建议按以下顺序推进：

1. 先改 `SectionCard`，支持 `headerRight`
2. 再抽 `EegHeaderSummary`
3. 再接入三张素材图和 `EegEmotionImagePanel`
4. 最后回收旧的 `Device / Latest Window / 实时脑电` 区块代码

这样做的好处是：

1. 每一步都可单独预览
2. 容易回退
3. 风险集中且可控
