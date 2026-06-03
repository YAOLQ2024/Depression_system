# VideoNode Transition Controller Step 3 实施说明

更新时间：2026-06-03

对应设计文档：

- `docs/apps/consultation/greeting-auto-advance-and-seamless-video-switch-design_20260602.md`

## 1. 本步产物

本步把视频节点切换状态机从页面组件里抽出，统一收口到 `features/video-node`。

代码入口：

- 纯状态机：`apps/consultation/client/src/features/video-node/controllerMachine.ts`
- 共享 hook：`apps/consultation/client/src/features/video-node/useVideoNodeTransitionController.ts`
- 通用 adapter factory：`apps/consultation/client/src/features/video-node/adapterFactory.ts`
- 咨询适配器：`apps/consultation/client/src/features/video-node/consultationTransitionAdapter.ts`
- 量表适配器：`apps/consultation/client/src/features/video-node/assessmentTransitionAdapter.ts`
- `VideoNode -> SeamlessVideoClip` 映射：`apps/consultation/client/src/features/video-node/clipMapping.ts`

## 2. Controller 统一状态

`useVideoNodeTransitionController` 统一维护：

- `currentNode`
- `prefetchedNode`
- `readyNode`
- `displayedNode`
- `pendingPreview`
- `pendingCommit`
- `transitionReason`

同时补充：

- `previewError`
- `commitError`

## 3. 共享能力

共享 hook 当前对外暴露：

- `currentClip`
- `preloadClip`
- `requestPreview()`
- `commitCurrentNode()`
- `applyResult(result)`
- `markReadyClip(clipKey)`
- `markDisplayedClip(clipKey)`
- `clearPrefetchedNode()`
- `reset()`

其中：

- `requestPreview()` 通过 adapter 调用 preview，并把结果落到 `prefetchedNode`
- `commitCurrentNode()` 通过 adapter 调用正式提交，并把结果收口回 `currentNode`
- `markReadyClip()` / `markDisplayedClip()` 负责承接 `SeamlessVideoPlayer` 的 ready/display 事件

## 4. 适配器边界

通用 adapter 仍沿用 Step 1 的统一接口：

- `getCurrentNode()`
- `canPreviewNextNode(currentNode)`
- `previewNextNode(currentNode)`
- `commitCurrentNode(currentNode)`
- `deriveNextNodeFromSubmitResult(result)`

当前已经落下两类接线入口：

- 咨询适配器：
  使用 `buildConsultationCurrentVideoNode(...)` 读取当前节点，并对接 consultation app actions 的 preview / complete 能力。
- 量表适配器：
  允许同时支持 `local_only` 的本地派生节点和 `submit_driven` 的 assessment session 返回结果派生。

## 5. 验证入口

静态 demo 页面已经改成：

- `adapter + useVideoNodeTransitionController + SeamlessVideoPlayer`

验证路由：

- `/labs/seamless-video-player`

在该页面中可以直接观察：

- `currentNode`
- `prefetchedNode`
- `readyNode`
- `displayedNode`
- `pendingPreview`
- `pendingCommit`
- `transitionReason`

## 6. 与完成标准对照

- 切换控制逻辑不再写死在某个页面组件里：
  已满足。共享状态机和 hook 已独立到 `features/video-node`，页面不再是唯一承载位置。
- 咨询和量表都能通过适配器接入同一控制层：
  已满足。`consultationTransitionAdapter.ts` 与 `assessmentTransitionAdapter.ts` 已提供统一适配入口。
- 控制层可以脱离具体页面做单元测试：
  已满足。`controllerMachine.ts` 是纯函数状态机，不依赖 React 页面组件，可单独做状态迁移测试。
