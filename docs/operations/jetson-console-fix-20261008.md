# 2026-10-08 问诊前端动画与控制台输出修复

- EEG 面板三组节点的两层光环及底座圆点，共七个半径动画缺少显式动画初始值。已在 HTTPS 问诊页和 StrictMode 组件检查中复现七次 `r="undefined"` 写入；为这些动画补充数值 `initial.r` 后，挂载、情绪切换、动画循环和面板重新展开均无报错。
- 移除音频调试函数的 `console.info`；保留最近 200 条 `window.__mcsAudioDebug` 内存记录，录音、上传及异常页面反馈逻辑保持原有行为。
- Docker 构建环境中的 TypeScript 检查及 Vite 生产构建通过。`make compose-config` 通过；`make phase-check` 完成，其中宿主机 FastAPI 可用性检查因未安装而跳过。
- 通过可信 HTTPS 的 Chromium 浏览器回归：登录、设备授权、打开问诊、展开/收起实时结果、录音五秒、上传及转写提交均通过；页面异常、控制台错误、失败请求、无效半径写入和音频控制台打印均为零。媒体设备为浏览器模拟设备。
- 首次复现时音频上传曾返回对象存储不可用；独立临时对象写入/删除检查通过，部署后完整录音提交回归未复现该错误。

## 部署与回退

当前问诊前端镜像为 `sha256:44febceb0456ce3d6cc9701809cd8c82870a69caf3d8e700039d4659ccfa54ca`。仅重新创建 `mcs-jetson-consultation-1`，HTTPS 就绪接口正常。

本次通过 Vite 的 `copyPublicDir: false` 构建应用代码，再将约 1.45 MB 构建产物加入原有问诊镜像；视频等公共资源复用基础镜像，运行期 React、Motion、路由及图表依赖的构建文件哈希与部署前一致。仓库标准 Dockerfile 未修改，后续常规构建仍会包含修复后的源码。旧哈希资源保留，以支持更新前已打开的页面；刷新页面后加载修复版本。

原镜像保留为 `mcs-jetson-consultation:before-console-fix-20261008`。如需回退，将该镜像重新标记为 `mcs-jetson-consultation:latest`，再执行 `./scripts/jetson-stack.sh up -d --no-deps consultation`。

私有复现记录、浏览器前后对比、构建文件和验收摘要保存在 `.codex-tmp/console-fix-20261008/`，不纳入 Git。
