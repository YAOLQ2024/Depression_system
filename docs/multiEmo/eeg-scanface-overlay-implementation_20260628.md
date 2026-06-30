# EEG 扫描人脸叠加层实施记录
更新时间：2026-06-28

## 本次落地的核心改法

1. 底图从“自带节点和脑网络的整图”切换为“纯 3D 扫描人脸底图”。
2. `Fpz / T7 / T8` 三个点位重新标定，不再沿用旧图坐标。
3. 脑网络、粒子、能量流全部收缩到额叶上半区、双颞叶连线区、颈部光束和底座区域。
4. 蓝 / 黄 / 绿三种状态不再只是换色，而是同步区分网络密度、粒子数量、流动方向和呼吸节奏。

## 资源与组件

- 底图资源：`apps/consultation/client/public/eeg-emotion/eeg-scanface-base.png`
- 主面板：`apps/consultation/client/src/components/eeg/EegHologramPanel.tsx`
- 几何与点位：`apps/consultation/client/src/components/eeg/eegHologramGeometry.ts`
- 动画参数：`apps/consultation/client/src/components/eeg/eegHologramTokens.ts`
- 粒子动画：`apps/consultation/client/src/components/eeg/EegParticleCanvas.tsx`

## 当前点位标定

- `Fpz`: `(160, 112)`
- `T7`: `(92, 178)`
- `T8`: `(228, 178)`

以上坐标基于 `320 x 480` 的内部视图坐标系。

## 三种情绪动效策略

- 蓝色消极：线条更少、更虚、更慢，粒子拖尾更短，整体下沉。
- 黄色中性：连接均匀稳定，呼吸节奏平缓，能量流保持对称。
- 绿色积极：粒子更多、拖尾更长，流动方向从 `Fpz` 向两侧扩散，整体略有上扬。

## 如果还要继续微调

优先只调这三类参数：

1. `eegHologramGeometry.ts` 里的三点坐标。
2. `eegHologramTokens.ts` 里的 `networkVisibleCount / particleCount / streamSpeed / bodyOffsetY`。
3. `EegParticleCanvas.tsx` 里的 `trailStep / trailLength / startY / endY`。

不要再改扫描人脸底图结构本身。
