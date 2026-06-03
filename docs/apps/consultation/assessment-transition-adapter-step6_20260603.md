# Step 6：量表会话适配器并接入共享控制层

## 变更目标

把 `ScaleQuestionnairePage` 从“量表页私有单 `<video>` 切换”改成“assessment adapter + `useVideoNodeTransitionController` + `SeamlessVideoPlayer`”。

## 本次落点

1. `ScaleQuestionnairePage.tsx` 接入共享 assessment adapter：
   - `createAssessmentVideoNodeTransitionAdapter(...)`
   - `useVideoNodeTransitionController(...)`
2. 阶段引导视频继续映射为 `local_only` 节点：
   - 尾声通过 `requestPreview()` 预热本阶段第 1 题
   - 引导结束后仅切本地 `playedStageIntros`，不走量表提交接口
3. 量表题目继续映射为 `submit_driven` 节点：
   - 题目视频播放完成后开放答题
   - 答题提交成功后，立刻把返回的下一节点送入 controller 预热
   - 保留原来的确认态延迟，再正式 `applyAssessmentSession(...)`
4. 页面播放器改为共享双层播放器：
   - 移除单 `<video>`
   - 移除动态 `key`
   - 接入 `SeamlessVideoPlayer`
5. 共享控制层补了两个能力：
   - `requestPreview()` 会复用正在进行的 preview promise
   - `primeNextNodeFromResult(...)` 支持 `submit_driven` 场景先预热、后正式切题

## 当前效果

- 阶段引导 -> 第 1 题切换现在走共享 controller 的本地 preview 预热，不再依赖单视频重建。
- 量表答题提交成功后，下一题或下一量表阶段的 intro 会先进入后台预热，再在确认态后切到前台。
- 量表页和咨询页现在都走同一套共享播放器内核与 VideoNode 控制层。

## 对照完成标准

- 量表阶段引导视频切换无白屏：已满足实现前提
- 量表内部题目切换无白屏：已满足实现前提
- 量表间切换观感一致：已满足实现前提，跨量表也走同一预热与切换链路
- 量表页不再维护独立的一套播放器切换逻辑：已满足
