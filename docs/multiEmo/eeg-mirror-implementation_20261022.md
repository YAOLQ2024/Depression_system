# EEG 情绪镜像融合实施记录

日期：2026-10-22。代码依据为当前 v20 SVM，保持原设备协议与预测方法。原视觉基准见 [融合方案](../../最终可视化设计方案_20261022/08_现有系统融合方案/01_融合落地方案.md)。

## 已加入的能力

- 问诊多模态看板中的内嵌情绪镜像：透明头像、外围网络、固定颜色、实时 EEG／判断依据、近期分类时间带。2026-10-24 起采用原位切换，取消初版展开 dialog。
- 复用原增量 SVG 波形；波形窗口仍为 4 秒，采集率与展示率分开显示。按名称将 Fpz、T7、T8 排列，不改变原数组中的通道对应关系。
- 头像类别来自最新真实分类；历史选择只改变解释。分类记录仅覆盖实际分析窗口，未知与缺失区间留灰，按有效时长统计近期主要类别。
- 新窗口保留 `sample_id`、`inference_id`、模型 SHA256 与精确输入：52→156→110。输入同时保存在私有推理 JSON 及原窗口 NPZ；live 和公开历史不发送私有向量。
- PostgreSQL 解释任务、跨轮次窗口分页、幂等请求、固定目标历史与三图联动。解释通过独立 CPU worker 执行，包含子进程硬超时、租约恢复、最多三次执行及提交令牌校验。
- 真实 Kernel SHAP 解释当前模型的指定类别 OvR decision score，三图共用 110 项归因；校验输出加和、跨导联分摊与数值有效性。
- 未配置参考集、旧窗口无输入快照、模型或参考版本不匹配时明确返回 unavailable；不使用原视频的模拟数值代替。

首期完整归因数组规模较小，随任务结果存入 PostgreSQL JSON，输入另随原 NPZ 归档至 MinIO。该实现简化了读取和恢复，不要求 worker 访问 MinIO。独立结果归档与长期清理可按数据保留策略后续补充。历史分页以样本创建时间和 UUID 保持稳定，目标及解释配置写入 cursor；旧解释仍可通过已知 ID 查询。

## 接口

浏览器统一经过 gateway，以 **multimodal_session_id** 为范围：

| 方法 | 路径（前缀 `/api/v1/multimodal/sessions/{id}/eeg`） | 用途 |
| --- | --- | --- |
| GET | `/windows?limit=20&cursor=...` | 真实窗口和分类摘要，跨 turn |
| POST | `/explanations` | body 为 `inference_id` 与 `target_class`（0／1／2） |
| GET | `/explanations/{explanation_id}` | 状态及完成结果 |
| GET | `/explanations?target_class=2&limit=20&cursor=...` | 同一解释配置的历史及固定色标 |

POST 对 queued／running 返回 202，其余返回 200；沿用 `{code,message,data}` 外壳。每次读取、创建均校验登录和资源所属会话。新接口对缺少 user_id 的旧无主会话拒绝访问。

三图使用 `sample_id + inference_id + config_hash` 关联；config_hash 包含模型、背景文件及 manifest 哈希、目标类、输出函数、映射和算法参数。计算服务启停不改变已完成解释的含义。前端使用请求取消及身份检查防止切换目标后的迟到响应覆盖当前数据。

## 部署

代码改动不会自动更新已运行的容器。按当前机器所用 Compose 组合重建 `multimodal-service`、`gateway-service` 和 `consultation`；新迁移 `20261022_0013` 由已有 `scripts/start.sh` 中的 Alembic 执行。无需替换 EEG 模型或重启 EEG bridge。

默认不开启新的 SHAP 计算。先完成正常问诊、波形和分类验收；缺少解释资产时仍能使用这些能力。

本机 Orin NX 启动现有镜像（包含 TensorRT 与 EEG bridge）：

```bash
cd /home/nvidia/Documents/depression-system
MCS_TENSORRT_ENABLED=true MCS_EEG_BRIDGE_ENABLED=true \
  ./scripts/orin-nx-stack.sh -p mcs-jetson up -d
```

更新上述三个服务时先 build，成功后再替换容器。以下构建命令直接联网，覆盖旧 Compose 配置中已失效的本地代理；运行时继续保留原 GPU Python 挂载和六层 Compose 配置：

```bash
MCS_TENSORRT_ENABLED=true MCS_EEG_BRIDGE_ENABLED=true \
  ./scripts/orin-nx-stack.sh -p mcs-jetson build \
  --build-arg HTTP_PROXY= --build-arg HTTPS_PROXY= \
  multimodal-service gateway-service consultation
MCS_TENSORRT_ENABLED=true MCS_EEG_BRIDGE_ENABLED=true \
  ./scripts/orin-nx-stack.sh -p mcs-jetson up -d --no-deps \
  multimodal-service gateway-service consultation
```

同一局域网的电脑可访问 `https://192.168.50.11/`。通过 SSH 使用时，在自己的电脑终端建立转发并保持连接：

```bash
ssh -N -L 8443:127.0.0.1:443 nvidia@192.168.50.11
```

随后在自己电脑的浏览器打开 `https://localhost:8443/`。用户名、设备地址、SSH 端口沿用实际连接参数；浏览器需要信任设备的本地 CA 证书。HTTPS 前端的 API 使用同一来源，只需转发这一端口。

真实解释需准备：

1. `services/multimodal-service/runtime-assets/eeg/background.npz`，包含 `scaled_features` 数组，形状 N×110，N 为 1–64（可配置，最大 128），全部有限值。
2. 同目录 `background.json`，与 NPZ 同名，结构如下；占位内容须替换为实际资产信息。

```json
{
  "background_id": "研究协议中固定的参考集版本",
  "background_sha256": "background.npz 的完整 SHA256",
  "model_sha256": "aaf90fdc32387575d54e063a2a434e3f0bb3bf089804c8a510392d6037fd2543",
  "pipeline_version": "window-zscore-mss-v1",
  "input_kind": "selected_scaled",
  "feature_names": ["按模型 selected_features 排序的 110 个完整名称"],
  "color_limit": 0.5,
  "influence_floor": 0.00000001
}
```

这里的 `color_limit` 只是字段格式示例，需用当前模型和验证数据确定。`feature_names` 必须是真正 110 项数组，来源为 `[model['trial_feature_names'][i] for i in model['selected_features']]`。参考数据必须经过与当前预测一致的窗口标准化、聚合、筛选和 scaler，不可直接拿原始 52 维、设计 CSV 或随机数接入。manifest 的哈希和名称核验不等于研究参考集的有效性验证。

启用真实计算时，向 API 与 worker 同时设置 `EEG_EXPLANATIONS_ENABLED=true`，并使用可选 profile：

```bash
# 标准环境；其他机器继续叠加其原有 -f 配置。
EEG_EXPLANATIONS_ENABLED=true docker compose \
  -f infra/compose/docker-compose.dev.yml \
  --profile eeg-explanations up -d --build \
  multimodal-service gateway-service consultation eeg-explanation-worker
```

本机 Orin NX 使用对应脚本保留原组合：

```bash
MCS_TENSORRT_ENABLED=true MCS_EEG_BRIDGE_ENABLED=true \
  EEG_EXPLANATIONS_ENABLED=true ./scripts/orin-nx-stack.sh -p mcs-jetson \
  --profile eeg-explanations up -d --build \
  multimodal-service gateway-service consultation eeg-explanation-worker
```

worker 使用 `Dockerfile.explanation`，CPU 并发 1，限制 1 CPU／768 MB；它不加载语音或视觉推理运行时。每个会话最多三个未完成任务；繁忙时新请求返回 `queue_busy`，释放资源后可重新请求，避免跟随最新窗口持续累积队列。默认采样预算 512、子进程超时 45 秒；超时按失败处理，最多三次，不在采集线程中等待。

停用新计算时将 API 的 `EEG_EXPLANATIONS_ENABLED=false` 并停止 worker；已有同配置完成解释仍可读。M1 固定会话校准模型的接入、完整光流形变、真实参考集稳定性和目标设备长期性能不属于本次已验证成果。

## 验证范围

验证记录见 [验证结果与合成数据截图](../test-evidence/eeg-mirror-20261022/README.md)。39 项后端测试、14 项前端测试通过。

验证范围：

- TypeScript 检查与 Vite 生产构建。
- EEG 波形与分类时间带测试：包括四秒缓冲、增量几何、时长加权、缺失留空与重叠区间去重。
- EEG 协议／运行时原有测试，新解释计算／PostgreSQL 集成测试，以及已有多模态 API 回归。
- 真实 Kernel SHAP 软件通路测试使用**合成训练与参考数据**；包括 110 维、输出加和、真实子进程执行与私有输入完整性。不构成真实受试者解释实验。
- 独立 PostgreSQL 测试数据库验证 migration、权限、跨会话拒绝、跨 turn 历史、cursor 配置隔离、幂等与租约恢复。
- Chromium 下通过临时合成数据测试页验证按钮、历史选择、目标切换迟到响应、当前头像保持、波形恢复、Esc、焦点恢复及 1080×1920 竖屏。该测试页不会进入应用交付。

真实设备上的端到端延迟、30 分钟联合运行、研究参考集来源与解释稳定性，仍需真实数据和目标设备验收。当前运行容器是否已替换，以部署实际执行记录为准。

2026-10-23 已完成本机三个目标服务的镜像重建、容器替换、数据库迁移及 HTTPS／API／CUDA 验证，EEG bridge 保持运行。详见 [实际部署记录](../test-evidence/eeg-mirror-20261022/deployment-20261023.json)。真实 SHAP 参考集仍未配置，新计算保持关闭。

## 2026-10-24 布局调整

EEG 卡片不再为了同屏展示其他模态而压缩高度。标题、实时 EEG／判断依据按钮及连接状态合并为一栏，移除重复大标题与放大按钮。波形区从 193px 增至 520px；工具栏、说明排在绘图区之外，三导联各约 130px。后续卡片自然向下排列，由右栏原有滚动区域容纳。

判断依据替换原波形区域，内容较多时自然增高；左侧头像仍表示当前分类。波形组件保持挂载，保留缩放与增量缓冲。原有滚轮纵向增益、Shift＋滚轮横向缩放、按钮缩放及双击复位不变。按卡片容器宽度响应布局：窄于 560px 时头像转为顶部摘要，波形保持 520px，不按浏览器总宽度错误压缩。

浏览器合成数据验证及截图见 [布局验收](../test-evidence/eeg-layout-20261024/README.md)。

### 同日比例回调（当前）

用户反馈首轮 520px 波形过高、头像过小。当前将实时区高度回调至 360px，头像／波形宽度恢复为初版接近的 40%／60%，分类徽标稍放大。500px 侧栏仍保留左右并排的完整头像；只有卡片窄于 420px 时才上下排列，头像卡片高度为 260px，取消原 104px 摘要头像。保留紧凑标题、原位切换及所有现有数据和缩放交互。

当前浏览器合成数据验证及截图见 [比例回调验收](../test-evidence/eeg-balance-20261024/README.md)，上一节 520px 记录作为首轮历史保留。

### 判断依据紧凑排版

移除按整个 EEG 卡片宽度强制堆叠两张解释摘要图的规则，改为两图并排、历史热图整行展示，并按解释区域本身的宽度适配图内布局。导联百分比独立使用 12px HTML 文本；宽区配头型示意，窄区只保留可读的导联数值。分组条形与热图行距收紧，目标／片段和历史操作合并，冗长说明按需展开。无数据、未计算与非情绪概率提示保留。

合成结果状态下，解释内容宽侧栏约 342px、500px 侧栏约 370px 高；采集、头像／波形比例和历史选择规则不变。详见 [判断依据排版验收](../test-evidence/eeg-explanation-20261024/README.md)。
