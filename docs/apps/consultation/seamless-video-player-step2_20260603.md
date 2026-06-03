# SeamlessVideoPlayer Step 2 实施说明

更新时间：2026-06-03

对应设计文档：

- `docs/apps/consultation/greeting-auto-advance-and-seamless-video-switch-design_20260602.md`

## 1. 本步产物

本步先独立落共享播放器壳，不改咨询页与量表页的业务推进逻辑。

代码入口：

- 共享播放器组件：`apps/consultation/client/src/components/video/SeamlessVideoPlayer.tsx`
- 共享导出：`apps/consultation/client/src/components/video/index.ts`
- 静态验证页面：`apps/consultation/client/src/pages/SeamlessVideoPlayerDemoPage.tsx`
- 验证路由：`/labs/seamless-video-player`

## 2. 组件职责

`SeamlessVideoPlayer` 当前职责：

- 始终常驻两个绝对定位重叠的 `<video>` 层
- 接收 `currentClip` 和 `preloadClip`
- 将 `preloadClip` 装载到后台层并执行预热
- 通过 `loadeddata/canplay` + `requestVideoFrameCallback()` 判定首帧 ready
- 当 `currentClip` 切换到已 ready 的后台层时，再执行显示层切换
- 切换完成后暂停旧前台层

## 3. 当前组件 API

输入：

- `currentClip`
- `preloadClip`
- `transitionDurationMs`
- `autoPlay`
- `muted`
- `controls`
- `loop`
- `className`
- `layerClassName`
- `videoClassName`

事件：

- `onClipReady`
- `onDisplayedClipChange`
- `onPlaybackBlocked`
- `onPlaybackStarted`
- `onTimeUpdate`
- `onEnded`
- `onVideoError`
- `onStateChange`

引用接口：

- `playDisplayed()`
- `pauseDisplayed()`
- `getDisplayedVideoElement()`
- `getPreloadVideoElement()`

## 4. 验证入口

静态 demo 页面使用真实本地视频资源：

- `/digital-human/consultation-v1/greeting-001.webm`
- `/digital-human/consultation-v1/chief-complaint-001.webm`
- `/digital-human/scale-assessment-v1/phq9-001.webm`

验证路由：

- `APP_PATHS.seamlessVideoDemo`
- 实际路径：`/labs/seamless-video-player`

页面右侧会显示：

- `currentClip`
- `preloadClip`
- `displayedClip`
- `activeLayerId`
- `Layer A/B` 当前 phase 与 ready 状态

## 5. 与完成标准对照

- 播放器容器不因节点变化重新挂载：
  组件内部固定渲染两个 `<video>` 层，切换只改 `src`、ready 状态与前后台显示层。
- 静态假数据可完成 A/B 双层无白屏切换：
  demo 页直接用固定 clip 列表驱动 `currentClip` / `preloadClip`，可连续切到下一段。
- `ConsultationPage` 和 `ScaleQuestionnairePage` 可在下一步接入：
  组件已经收口为共享路径，并采用 `currentClip + preloadClip` 形式，后续 `useVideoNodeTransitionController` 可直接投喂 `VideoNode -> Clip` 映射结果。
