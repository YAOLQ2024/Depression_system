# Step 5：咨询会话适配器并接入共享控制层

## 变更目标

把 `ConsultationPage` 从“页面内硬编码自动推进 + 单 `<video>` 重建”切到“consultation adapter + `useVideoNodeTransitionController` + `SeamlessVideoPlayer`”。

## 本次落点

1. `ConsultationPage.tsx` 接入共享 consultation adapter：
   - `createConsultationVideoNodeTransitionAdapter(...)`
   - `useVideoNodeTransitionController(...)`
2. 自动推进链路改为共享控制层驱动：
   - `handleVideoTimeUpdate()` 在尾声调用 `requestPreview()`
   - `handleVideoEnded()` 调用 `commitCurrentNode()`
3. 页面播放器改为共享双层播放器：
   - 移除单 `<video>`
   - 移除动态 `key`
   - 接入 `SeamlessVideoPlayer`
4. 播放器事件接回共享状态机：
   - `onClipReady -> markReadyClip(...)`
   - `onDisplayedClipChange -> markDisplayedClip(...)`
5. 共享控制层补了一层 preview 去重保护，已存在下一节点预取时不再重复请求。

## 当前效果

- `greeting-001` 尾声会先走 `preview-complete`，只预热下一题，不提前正式提交。
- 当前节点结束后才走正式 `commit`，并立即把已预热的视频切到前台层。
- 咨询会话内部节点切换不再依赖单 `<video>` 重挂载，因此切换过程中播放器容器保持常驻。

## 对照完成标准

- `greeting-001` 尾声会触发 preview，不提前真实提交：已满足
- `greeting-001 -> chief-complaint-001` 等待显著缩短：已满足实现前提，需联调时做主观观感确认
- 咨询会话内部题目切换不再白屏：已满足实现前提，页面已改为共享 A/B 双层播放器
- 咨询会话跨阶段切换观感一致：已满足实现前提，跨阶段仍走同一 controller/player 链路
