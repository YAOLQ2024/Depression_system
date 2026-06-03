# VideoNode Step 1 边界与映射

更新时间：2026-06-03

对应设计文档：

- `docs/apps/consultation/greeting-auto-advance-and-seamless-video-switch-design_20260602.md`

本文件记录 Step 1 已经在代码中落下的统一抽象，作为 Step 2 `SeamlessVideoPlayer` 与 Step 3 `useVideoNodeTransitionController` 的接线边界。

## 1. 共享边界

前端视频节点框架统一收口为三层：

- 共享播放器：`SeamlessVideoPlayer`
- 共享切换控制层：`useVideoNodeTransitionController`
- 会话适配层：`session video node adapter`

当前代码入口：

- 共享类型与边界定义：`apps/consultation/client/src/features/video-node/types.ts`
- 咨询当前节点映射：`apps/consultation/client/src/features/video-node/consultationVideoNode.ts`
- 量表当前节点映射：`apps/consultation/client/src/features/video-node/assessmentVideoNode.ts`

页面组件只消费 `currentVideoNode`，不再新增“某页面专用视频逻辑”命名的共享能力。

## 2. 统一 VideoNode 结构

统一字段：

- `nodeKey`
- `questionKey`
- `sessionKind`
- `source`
- `transitionMode`
- `stageId`
- `stageLabel`
- `stageOrder`
- `videoAssetId`
- `videoUri`
- `displayText`
- `subtitleText`
- `responseRequired`

统一 `transitionMode`：

- `auto_commit`
- `submit_driven`
- `local_only`

## 3. 现有视频节点映射

- 咨询系统题视频：`consultation_system_question` -> `auto_commit`
- 咨询普通题视频：`consultation_question` -> `submit_driven`
- 量表阶段引导视频：`assessment_stage_intro` -> `local_only`
- 量表题目视频：`assessment_question` -> `submit_driven`

映射结果已经在页面侧接入：

- `ConsultationPage.tsx` 通过 `buildConsultationCurrentVideoNode(...)` 读取当前 `VideoNode`
- `ScaleQuestionnairePage.tsx` 通过 `buildAssessmentCurrentVideoNode(...)` 读取当前 `VideoNode`

## 4. 命名约束

后续新增视频切换能力时遵循以下约束：

- 先映射为 `VideoNode`，再进入播放器或切换控制层
- 不新增 `ConsultationPage*Video*` / `ScaleQuestionnairePage*Video*` 这类共享能力命名
- 页面只负责声明当前节点与事件接线，不负责发明新的播放器切换语义
