# EEG 看板布局验收

日期：2026-10-24。截图与浏览器记录使用**合成波形、合成分类和合成贡献值**，不代表设备采集或受试者结果。临时验证入口已从前端源码目录移出，不进入产品构建。

详见 [浏览器验证记录](verification.json)。

- 波形区实际高度 520px；三导联各 130px；宽容器标题栏高度 53px。
- 判断依据在原位显示，没有 dialog，切换时右栏滚动位置不变。
- 波形节点保持挂载，缩放状态保留，返回后波形继续更新。
- 现有按钮缩放、滚轮、Shift＋滚轮及双击复位检查通过。
- 历史选择保留当前头像，迟到的目标响应不会覆盖当前解释；参考集缺失时保留无数据状态。
- 500px 侧栏、1080×1920 竖屏和 390px 窄屏检查通过，无横向溢出；后续模态可通过侧栏滚动到达。
- TypeScript、14 项 EEG 前端测试、Vite 生产构建、Compose 配置和 phase-check 通过。phase-check 的宿主机 FastAPI 探测仍报告未安装；本次只修改前端。

前端 Docker 已重建并替换，HTTPS 实际提供的新 EEG 模块与镜像资源一致；网关、多模态服务和 EEG bridge 容器 ID 保持不变。详见 [部署校验](deployment.json)。在原访问地址强制刷新即可加载新布局。

合成数据截图：

- [宽侧栏实时波形](synthetic-live-wide.png)
- [原位判断依据](synthetic-explanation-inline.png)
- [窄侧栏实时波形](synthetic-live-sidebar.png)
- [竖屏实时波形](synthetic-live-portrait.png)
