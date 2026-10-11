# 竖屏男医生视频资源

原始资源来自 `/home/jetson/Documents/ZR/竖屏男医生_webm`，此目录中的视频文件名已统一为现有横屏资源的节点命名。

## 临时素材

`问诊（consultation-v1）/risk-screening-003.webm` 暂时复制自 `../consultation-v1/risk-screening-003.webm`，使用的是原横屏人物形象，供开发阶段衔接流程。朱睿完成对应男医生视频后，保持文件名不变替换此文件，并移除 `src/lib/digitalHumanResources.ts` 中 `getDigitalHumanLayout` 对该文件的横屏比例例外。

前端映射由 `src/lib/digitalHumanResources.ts` 统一维护。问诊、量表、结果解读、干预入口的播放器按浏览器方向选择资源；横屏保持原路径，竖屏使用此目录。题目节点与答案状态不随方向切换而改变，新旧视频时长不同时按已播放比例恢复位置。

现有横屏视频 URL 中的片尾裁剪时间不应用到男医生素材，男医生视频使用自身完整时长。`portrait-male-poster.png` 从问诊开场视频提取，用于首页和准备页的竖屏静态人物展示。
