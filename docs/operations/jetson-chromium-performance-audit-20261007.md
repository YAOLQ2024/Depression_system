# 开发板 Chromium 卡顿排查（2026-10-07）

本次仅诊断：读取运行状态和代码、检查独立临时 Chromium 实例、进行短时只读请求采样。没有修改浏览器设置、项目代码、服务配置、内存或磁盘分区，也没有重启用户正在使用的浏览器。临时浏览器实例已退出。

当前最值得优先排查的是 Chromium 图形驱动初始化失败后使用软件合成和软件视频解码。视频、持续动画及摄像头采样可能叠加这一负载。上传接口另有阻塞事件循环的代码风险，适用于“上传时其他请求变慢”这一类现象，尚未与用户此次卡顿建立时间对应关系。

## 1. 已确认：图形合成与视频硬解没有启用

正在使用的浏览器是 **Flatpak `org.chromium.Chromium` 146.0.7680.80 / aarch64**。活动页面的 renderer 进程带有 `--disable-gpu-compositing`，GPU 进程带有 `--use-gl=disabled`。

使用同一 Flatpak 浏览器、独立临时配置和本机 X11 桌面检查，CDP `SystemInfo.getInfo` 返回：

```text
gpu_compositing: disabled_software
rasterization: disabled_software
2d_canvas: disabled_software
video_decode: disabled_software
glRenderer: Disabled
videoDecoding: []
```

图形实例日志包括：

```text
glXQueryExtensionsString returned NULL
eglInitialize OpenGL failed with error EGL_NOT_INITIALIZED
Initialization of all EGL display types failed.
```

另一个 headless 实例识别到 Mesa llvmpipe 软件渲染，视频解码亦为 software。结论主要依据图形实例及正在运行的用户浏览器，不依赖 headless 结果。

Flatpak 检测到宿主机 `nvidia-540-4-0` 驱动标识，而实际运行时挂载的是 `org.freedesktop.Platform.GL.default` 的 Mesa 扩展，没有看到对应 NVIDIA 图形扩展。**Flatpak 图形库与 Jetson 图形驱动兼容性是优先核查方向**，但尚未通过修复后对比证明是唯一根因。Flatpak 的 GL 扩展选择机制见[官方文档](https://docs.flatpak.org/en/latest/extension.html)。

对原有浏览器进程进行 8 秒采样：软件 GPU 进程约占一个 CPU 核的 43%，活动 renderer 约 24.5%。这是该短时间窗口的值，不能作为每次卡顿峰值或整机 CPU 满载的证明。

浏览器的图形合成机制参见 [Chromium 官方说明](https://www.chromium.org/developers/design-documents/gpu-accelerated-compositing-in-chrome/)。

## 2. 已确认的媒体与动画负载，具体贡献待测

- 两个检查过的数字人素材 `greeting-001.webm`、`risk-screening-review-002.webm` 都是 **1920×1080、30 fps、VP9、`ALPHA_MODE=1`**。当前浏览器用 CPU 解码和合成这些视频，透明画面还需叠加到页面背景。
- 已有 `__MCS_PERFORMANCE_MODE__=true` 生效，页面 `data-performance-mode=true`。背景模糊的部分规则已关闭，播放器也限制后台视频预加载。因此不能把“性能模式没打开”或“始终预解码两路视频”直接列为本次原因。
- 性能模式仍保留多处持续动画。`EegParticleCanvas.tsx:216` 开始的绘制循环每帧查询显示尺寸、清空并重绘粒子与光晕；该循环没有固定帧率限制。它是否影响用户当时页面取决于相关面板是否挂载。
- `HomeOrbitalMenu.tsx:41` 的 requestAnimationFrame 循环在到达目标角度后仍继续调度。React 对相同状态值可能跳过重渲染，因此应区分持续回调成本与实际组件重渲染，不能将其等同于每帧重绘整个页面。
- 问诊摄像头请求 ideal 960×720，没有限制 frameRate；实际分辨率和帧率取决于设备协商。`useVisualCapture` 默认每 1500 ms 捕获一次全尺寸图像；`captureVideoFrame` 每次新建 canvas，执行 drawImage 和 JPEG 编码。
- 录音期间每 100 ms 更新计时状态；实时状态的非 EEG 部分按 180 ms 合并。EEG 波形已有 50 ms 绘制间隔，不能概括为所有实时模块均无限制刷新。

以上是实际代码中的负载候选，还没有在用户发生卡顿的原页面上采集 Performance trace 或掉帧数据，不能给出各自占比。

## 3. 内存换页可能放大延迟，未见持续大量换页

最初采样：物理内存 7619 MiB、已用 5509 MiB、available 1817 MiB；swap 已用 4770 MiB。10 秒 vmstat 窗口中有间歇换入，约 0–1764 KiB/s，没有持续 swap-out，I/O wait 基本为 0%。

这说明之前存在内存压力，切回不活跃的页面或模型时可能出现页面换入等待；**swap 占用数值本身不证明当前正在严重换页**。本轮没有调整内存。磁盘剩余约 8.1 GiB，短采样未显示明显 I/O 等待。

温度样本约 49–50℃；电源模式已是 `MAXN_SUPER`。当前证据没有显示明显热压力或处于低功耗模式。

## 4. 上传与提交等待存在独立的后端原因

`services/gateway-service/app/api/multimodal.py` 的音频上传、音频状态读取及图像上传为 `async def`，但直接调用同步转发函数。其中 `clients/multimodal_client.py:100` 使用阻塞式 `urllib.request.urlopen` 并读取上游响应。这些调用没有转移到线程或异步 HTTP 客户端，可能阻塞当前 Uvicorn worker 的事件循环，导致其他请求和实时事件等待。此风险与浏览器掉帧是不同路径，参见 [FastAPI 并发文档](https://fastapi.tiangolo.com/async/)及 [Python asyncio.to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)。

ASR 的 ThreadPoolExecutor 为 `max_workers=1`。多路录音同时提交时会排队，首次加载模型也可能增加等待。前端默认每 200 ms 查询转写状态。

只读取之前合成测试账号的音频记录：4–5 秒音频两条记录的 `updated_at-created_at` 约 1.26、1.39 秒。该值是记录处理时间，不能当作纯 ASR 耗时，也不代表用户当前录音。

本轮没有生成新录音、提交新推理任务或读取真实用户转写内容。

## 5. 当前短采样中的网络与证书情况

独立图形 Chromium 实例严格校验证书后成功打开 LAN HTTPS，确认 secure context 为 true。

本机访问首页/config.js 的首次 curl 请求约 94–105 ms；下载 6,592,918 字节问候视频约 118 ms。另对无认证 `/api/v1/users/me`（预期 401）和 config.js 做 16 组并行只读采样：

| 请求 | 中位耗时 | 最大耗时 |
| --- | --- | --- |
| 网关 API | 21.65 ms | 36.7 ms |
| config.js | 21.8 ms | 35.9 ms |

该窗口没有观察到明显网络等待或网关停顿；没有覆盖用户实际提交录音期间，不能排除上述上传阻塞问题。无认证 API 也不能代替业务 API 的性能验证。

## 建议处理顺序

1. 先验证 Jetson 图形驱动与浏览器运行环境兼容，使 GPU compositing/rasterization 能正常启用；图形合成和视频解码分别检查，不能只看浏览器设置开关。必要时对可用的 Jetson 兼容浏览器做独立对比，保留现用环境直到验证通过。
2. 对数字人素材制作保留透明通道的 720p 版本并对比掉帧、清晰度和 CPU，先不要覆盖原素材。若考虑 H.264 等不含当前透明通道的格式，需要同时评估合成背景方案。
3. 将持续粒子/装饰动画降到 15–20 fps，在不可见或后台时停止；菜单收敛后停止 RAF；限制 canvas 像素密度，减少每帧布局读取。针对实际卡顿页面测量后再决定范围。
4. 对摄像头预览试验 640×480 / 15 fps，并将分析采样与显示预览分开，核查是否影响表情/姿态输入质量。
5. 修复网关异步接口中的同步转发调用，再测录音上传期间其他接口的响应；对录音处理分阶段记录耗时。ASR 并发度应依据板端内存和 GPU 负载评估，不直接增加线程数。

图形诊断、CPU 和请求采样原始数据保留在 `.codex-tmp/perf-audit/`，已被 Git 忽略。这些结论是本次快照及代码分析，尚未提供用户具体卡顿页面的修复前后对比。
