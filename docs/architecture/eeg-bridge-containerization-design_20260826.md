# EEG 蓝牙桥接程序容器化设计

更新时间：2026-08-26

## 1. 背景与目标

当前 Windows 开发链路需要在 Docker 业务服务之外，额外启动宿主机
`eeg-tools bridge` 或 `eeg-bridge.exe`：

```text
EEG 设备
  -> Windows 宿主机 eeg-tools / eeg-bridge.exe
  -> Redis Stream
  -> Docker 内 multimodal-service
  -> EEG 解码、特征提取和模型推理
```

该方式主要用于绕过 Windows Docker Desktop 对宿主机蓝牙设备访问和透传的限制。
迁移到 Linux / Jetson 后，宿主机可以通过 BlueZ 管理蓝牙设备，容器通过 system
D-Bus 调用 BlueZ，因此可以把 EEG 蓝牙桥接进程转化成独立容器。

本次目标是：

1. 把真实 EEG 蓝牙采集程序封装为 `eeg-bridge` 容器。
2. 用户通过 Docker Compose 启动整套系统，不再手工运行 PowerShell 或 EXE。
3. 保留独立 bridge 与 `multimodal-service` 的服务边界。
4. 保证 BLE 原始字节、Redis Stream key、Redis Entry 格式、编码方式、批处理行为和下游解码行为完全不变。
5. 支持蓝牙和 Redis 断线后的自动恢复，并提供可观测的运行状态。

本次不修改：

- EEG 设备端协议；
- BLE Service / Characteristic 协议；
- EEG 数据包解析算法；
- EEG 通道顺序、采样率和字节序；
- EEG 特征工程；
- EEG 模型及推理窗口；
- Redis Stream 消费协议；
- 前端 EEG 波形协议。

## 2. 设计原则

### 2.1 只改变部署边界

容器化只改变 bridge 进程的运行位置：从 Windows 宿主机进程变为 Linux 容器。
从 BLE Notification 回调取得 `bytes` 后，原有处理函数和数据路径全部复用。

### 2.2 bridge 只做传输适配

`eeg-bridge` 负责：

- 扫描和连接 BLE 设备；
- 订阅 Notify Characteristic；
- 接收原始 BLE 字节；
- 按当前规则批量合并 Notification；
- 写入 Redis Stream；
- 记录连接、队列、发布和丢包状态；
- 按配置可选录制原始 JSONL。

`eeg-bridge` 不负责：

- EEG 包解析；
- 通道数据换算；
- 特征提取；
- 模型推理；
- consultation session / turn 绑定；
- 数据库存储；
- 前端实时推送。

这些职责继续由 `multimodal-service` 承担。

### 2.3 协议兼容优先

首轮落地不同时进行消息优化、可靠性改造、最小权限改造或网络结构调整。
任何可能改变消息内容、消息边界、时序或异常处理结果的优化，都应在容器化验收后单独立项。

## 3. 目标架构

```text
┌──────────────────┐
│ EEG BLE device   │
└────────┬─────────┘
         │ BLE Notify：原始 bytes
         ▼
┌──────────────────┐
│ Linux kernel     │
│ + host BlueZ     │
│ + bluetoothd     │
└────────┬─────────┘
         │ system D-Bus
         │ /run/dbus/system_bus_socket
         ▼
┌────────────────────────────────────┐
│ eeg-bridge container               │
│                                    │
│ BleakScanner / BleakClient         │
│ -> 原有 packet queue               │
│ -> 原有 batch concat               │
│ -> 原有 RedisStreamWriter          │
└────────┬───────────────────────────┘
         │ Redis Stream
         │ mcs:eeg:transport:default
         ▼
┌────────────────────────────────────┐
│ Redis                              │
└────────┬───────────────────────────┘
         │ XREADGROUP
         ▼
┌────────────────────────────────────┐
│ multimodal-service                 │
│                                    │
│ EEGRedisStreamProvider             │
│ -> EEGPacketDecoder                │
│ -> 特征提取                        │
│ -> model_combined_3class.pkl       │
│ -> 推理、入库和实时状态            │
└────────────────────────────────────┘
```

BlueZ 和 `bluetoothd` 只运行在 Linux 宿主机。容器不启动第二套
`bluetoothd`，也不直接接管蓝牙 USB 适配器，而是通过挂载的 system D-Bus
socket 使用宿主机 BlueZ。

## 4. 协议冻结规范

本节是容器化实施期间的强约束。除时间戳、Redis Entry ID 等运行时动态值外，
生产端和消费端可观察到的协议不得变化。

### 4.1 BLE 接入参数

保持现有配置项和匹配规则：

```env
EEG_DEVICE_NAME_HINT=EEG
EEG_NOTIFY_CHAR_UUID=6e400003-b5a3-f393-e0a9-e50e24dcca9e
EEG_SCAN_SECONDS=5
EEG_RECONNECT_DELAY_SECONDS=5
```

要求：

- 继续用设备名称、本地广播名称或设备地址匹配 `EEG_DEVICE_NAME_HINT`；
- 继续订阅相同 Notify Characteristic；
- Notification 回调内只执行 `bytes(data)`，不解析、不补齐、不截断；
- 不修改包头、包尾、通道顺序、采样点表示方式和字节序；
- 不在 bridge 中加入 EEG 帧边界判断，半包和粘包继续交由下游流式解码器处理。

### 4.2 批处理和拼接行为

当前 bridge 使用有界队列缓存 BLE Notification，并在以下边界内形成发布批次：

```env
EEG_HOST_BRIDGE_QUEUE_MAXSIZE=2048
EEG_HOST_BRIDGE_PUBLISH_BATCH_SIZE=32
EEG_HOST_BRIDGE_PUBLISH_BATCH_TIMEOUT_MS=20
```

一个 Redis Entry 的 payload 必须继续按接收顺序生成：

```python
combined_payload = b"".join(item.payload for item in batch)
```

容器化期间禁止改为“一条 BLE Notification 对应一条 Redis Entry”，也禁止修改
batch size、batch timeout、队列满时的丢弃方向或排序方式。

### 4.3 Redis Stream key

固定共享前缀：

```env
EEG_STREAM_KEY_PREFIX=mcs:eeg:transport
```

生产端与消费端继续使用当前派生规则：当最后一段为 `transport` 时，实际 key 为：

```text
mcs:eeg:transport:default
```

不要在一端配置前缀、另一端配置完整 key，也不要引入新的设备后缀、部署环境后缀
或版本后缀。

### 4.4 Redis Entry 格式

Redis Stream 中每条 Entry 继续使用下列字段：

| 字段 | 必需性 | 格式 | 语义 |
|---|---:|---|---|
| `ts` | 必需 | 十进制整数字符串 | 批次最后一个 Notification 的 UTC Unix 毫秒时间戳 |
| `received_at` | 必需 | UTC ISO-8601，`Z` 结尾 | 批次最后一个 Notification 的接收时间 |
| `first_received_at` | 批处理时存在 | UTC ISO-8601，`Z` 结尾 | 批次第一个 Notification 的接收时间 |
| `source` | 必需 | 字符串 | bridge 来源标识 |
| `packet_count` | 必需 | 十进制整数字符串 | 本 Entry 合并的 Notification 数量，最小为 1 |
| `device_id` | 设备地址可用时存在 | 字符串 | Bleak 返回的设备地址/标识 |
| `payload_hex` | 必需 | 小写十六进制字符串 | 合并后的原始 BLE 字节 |

示意消息：

```json
{
  "ts": "1787702400123",
  "received_at": "2026-08-26T08:00:00.123Z",
  "first_received_at": "2026-08-26T08:00:00.105Z",
  "source": "windows_host_bridge",
  "packet_count": "4",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "payload_hex": "aa550102..."
}
```

虽然消费者兼容 `payload_base64` 和原始 `payload`，容器 bridge 必须继续显式使用：

```env
EEG_HOST_BRIDGE_PAYLOAD_ENCODING=hex
```

不得借容器化切换到 Base64 或 Redis binary field。

### 4.5 `source` 字段

当前 Windows 默认值为：

```env
EEG_HOST_BRIDGE_SOURCE=windows_host_bridge
```

现有 Linux Compose 草案使用 `jetson_eeg_bridge`。虽然下游当前不依赖该值进行
字节解码，但严格而言这属于协议字段值变化。首轮零变化迁移应继续设置：

```env
EEG_HOST_BRIDGE_SOURCE=windows_host_bridge
```

如果未来要改为部署无关的 `eeg_bridge`，必须作为独立协议变更，经上下游确认并
更新测试基线后实施。

### 4.6 消费端行为

保持：

```env
MCS_CONTAINER_EEG_PROVIDER=redis_stream
EEG_STREAM_CONSUMER_GROUP=multimodal-eeg
```

`multimodal-service` 继续：

1. 优先读取 `payload_hex`；
2. 执行 hex 到 bytes 的无损还原；
3. 把完整 bytes 传入现有 `EEGPacketDecoder`；
4. 处理成功或失败后执行 `XACK`；
5. 不根据容器来源增加新的解析分支。

## 5. 容器设计

### 5.1 镜像

复用现有 `services/eeg-bridge/Dockerfile`，基础结构保持：

- Python 3.11 slim；
- 安装 BlueZ、D-Bus 和 GLib 运行依赖；
- 安装 `tools/eeg-tools/requirements.txt`；
- 复制 `tools/eeg-tools`；
- 设置 `PYTHONPATH=/app/tools/eeg-tools/bridge-runtime`；
- 入口为 `python -m app.main`。

不要复制 EEG 模型或整个 `multimodal-service` 到 bridge 镜像。

建议后续补充但不影响协议的镜像能力：

- 固定 Python 和系统依赖版本；
- 以 exec-form 启动，保证 SIGTERM 能传递给 Python；
- 增加镜像标签和构建版本；
- 增加非 root 可运行性验证；
- 增加只读根文件系统验证。

### 5.2 BlueZ / D-Bus

Compose 保留：

```yaml
volumes:
  - /run/dbus/system_bus_socket:/run/dbus/system_bus_socket
```

启动前检查：

1. `/run/dbus/system_bus_socket` 存在；
2. 宿主机 `bluetooth.service` 正常；
3. 蓝牙适配器未被 rfkill 禁用；
4. `bluetoothctl show` 能看到 Controller；
5. 宿主机能扫描到 EEG 广播；
6. 没有其他程序长期占用 EEG GATT 连接。

### 5.3 权限

第一阶段保留现有：

```yaml
privileged: true
```

原因是第一阶段的验收目标是功能和协议等价，不能同时引入 BlueZ D-Bus policy、
Linux capability 和用户权限差异。

通过等价性和稳定性验收后，再单独执行权限收缩：

1. 验证仅挂载 system D-Bus socket 是否足够；
2. 为容器用户配置最小 BlueZ D-Bus policy；
3. 仅添加实际需要的 capability；
4. 尝试只读挂载 D-Bus socket；
5. 移除 `privileged: true`；
6. 验证扫描、连接、Notify、断线重连全部正常。

权限收缩不得与首轮容器化合并交付。

### 5.4 网络

第一阶段保留现有：

```yaml
network_mode: host
```

bridge 使用：

```env
REDIS_URL=redis://127.0.0.1:${REDIS_PORT:-6379}/0
```

前提是 Redis 端口发布到 Linux 宿主机，且端口与 `REDIS_PORT` 一致。如果 Redis
启用密码或 TLS，bridge 必须使用与业务服务一致的连接参数。

协议等价验收后可以把 bridge 接入 Compose 网络，并改用
`redis://redis:6379/0`。这不会改变 Redis Entry 格式，但属于部署拓扑调整，应单独
验证，不与首轮迁移同时进行。

### 5.5 数据卷

保留两个独立卷：

```yaml
volumes:
  - eeg_bridge_data:/app/tools/eeg-tools/data
  - eeg_bridge_tmp:/app/tools/eeg-tools/tmp
```

用途：

- `data`：按配置保存 JSONL 原始录制文件；
- `tmp`：保存 bridge 状态文件。

默认关闭录制：

```env
EEG_HOST_BRIDGE_RECORD_ENABLED=false
```

需要问题复现时显式开启，并配置磁盘容量、保留期和敏感数据清理策略。

## 6. 推荐运行配置

业务消费端：

```env
MCS_CONTAINER_EEG_ENABLED=true
MCS_CONTAINER_EEG_PROVIDER=redis_stream
MCS_CONTAINER_EEG_AUTO_START_TRANSPORT=true
MCS_CONTAINER_EEG_REQUIRE_TRANSPORT_FOR_READY=true

EEG_STREAM_KEY_PREFIX=mcs:eeg:transport
EEG_STREAM_CONSUMER_GROUP=multimodal-eeg
```

bridge：

```env
EEG_DEVICE_NAME_HINT=EEG
EEG_NOTIFY_CHAR_UUID=6e400003-b5a3-f393-e0a9-e50e24dcca9e
EEG_SCAN_SECONDS=5
EEG_RECONNECT_DELAY_SECONDS=5

EEG_HOST_BRIDGE_SOURCE=windows_host_bridge
EEG_HOST_BRIDGE_PAYLOAD_ENCODING=hex
EEG_HOST_BRIDGE_QUEUE_MAXSIZE=2048
EEG_HOST_BRIDGE_PUBLISH_BATCH_SIZE=32
EEG_HOST_BRIDGE_PUBLISH_BATCH_TIMEOUT_MS=20
EEG_HOST_BRIDGE_REDIS_MAXLEN=5000
EEG_HOST_BRIDGE_REDIS_APPROX_MAXLEN=true
EEG_HOST_BRIDGE_RECORD_ENABLED=false
```

根 `.env` 中当前 EEG 为关闭状态。正式启用 Linux bridge 时，需要显式修改为上述
业务消费端配置，避免出现 bridge 正常发布但 `multimodal-service` 没有启动消费者的
情况。

## 7. Compose 组织与启动方式

继续把 Linux EEG bridge 作为显式 overlay：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build
```

如需 GPU：

```bash
docker compose \
  -f infra/compose/docker-compose.dev.yml \
  -f infra/compose/docker-compose.gpu.yml \
  -f infra/compose/docker-compose.jetson-eeg-bridge.yml \
  up -d --build
```

约束：

- 同一环境只允许一个真实 bridge 生产者连接 EEG 设备；
- bridge 和 replay 默认互斥，不得同时写入相同 Stream；
- Windows 默认 Compose 不加载 Linux EEG overlay；
- Linux 部署不再启动 Windows EXE 或宿主机 Python bridge；
- replay 继续保留为测试、验收和故障复现工具。

## 8. 健康检查与可观测性

### 8.1 三种状态必须分离

#### 容器存活状态

用于 Docker healthcheck，判断：

- 主进程仍在运行；
- 状态文件能够产生并持续更新；
- 未发生不可恢复的初始化错误。

#### 蓝牙连接状态

沿用当前状态：

```text
idle
scanning
connecting
connected
streaming
disconnected
stopped
```

`scanning` 或 `disconnected` 表示 EEG 设备暂时不可用，不表示 bridge 进程死亡，
因此不能仅因未发现设备而让 Docker healthcheck 失败并进入无限重启。

#### 数据链路就绪状态

业务 readiness 应综合判断：

- EEG 功能已启用；
- `multimodal-service` 的 Redis Stream provider 已运行；
- bridge 可以访问 Redis；
- bridge 最近有成功发布；
- `multimodal-service` 最近有收到数据；
- 数据格式能被下游解码。

### 8.2 指标和日志

至少保留并监控：

- `status`；
- `device_id`；
- `packet_count`；
- `publish_count`；
- `published_packet_count`；
- `dropped_packet_count`；
- `last_packet_at`；
- `last_publish_at`；
- `last_stream_entry_id`；
- `last_batch_packet_count`；
- `queue_size`；
- `queue_capacity`；
- `last_error`。

Redis 侧补充观察：

- Stream 长度；
- consumer group lag；
- pending entry 数量；
- 最后 Entry ID；
- 消费端最后收到数据的时间。

## 9. 故障处理策略

### 9.1 蓝牙断线

沿用当前行为：

```text
断线
  -> 等待 EEG_RECONNECT_DELAY_SECONDS
  -> 重新扫描
  -> 匹配设备
  -> 重新连接
  -> 重新订阅 Notify
```

蓝牙断线不重启 Redis、`multimodal-service` 或整个 Compose 项目。

### 9.2 Redis 暂时不可用

沿用当前实现：发布失败后关闭当前 Redis client，后续发布时重新建立连接。

当前实现中，发布失败的 batch 最终仍会从本地队列移除，不会自动重新入队，Redis
故障窗口内可能丢失 EEG 数据。这是既有语义。为了满足“协议和行为不变”，首轮
容器化不修改该策略，只通过 `last_error`、计数器和日志暴露故障。

如需 at-least-once 重试、磁盘缓冲或 WAL，应单独设计可靠性协议，并评估重复消息、
乱序和模型窗口边界影响。

### 9.3 队列满

沿用当前行为：

- 有界队列；
- 队列满时丢弃新到达的数据包；
- 增加 `dropped_packet_count`；
- 限频输出告警。

首轮不修改为覆盖旧包或阻塞 BLE 回调。

### 9.4 容器重启

使用：

```yaml
restart: unless-stopped
```

容器重启后重新扫描和连接设备。Redis Stream consumer group 由
`multimodal-service` 管理，bridge 不创建、删除或重置 consumer group。

## 10. 协议零变化测试

### 10.1 Golden fixture

建立固定 BLE Notification 序列，覆盖：

- 单个完整帧；
- 一个 Notification 包含多个帧；
- 一个帧跨多个 Notification；
- 包头跨 Notification；
- 含噪声和非法前缀；
- 最大 batch；
- batch timeout；
- 多个连续 batch。

同一输入分别执行现有宿主机实现和容器实现。归一化以下动态值后逐字段比较：

- Redis Entry ID；
- `ts`；
- `received_at`；
- `first_received_at`；
- 测试环境导致变化的 `device_id`。

必须完全相同：

- Stream key；
- Entry 字段集合；
- 字段类型；
- `source`；
- `packet_count`；
- payload 字段名称；
- `payload_hex` 内容；
- Redis Entry 数量；
- Notification 拼接顺序；
- batch 边界。

### 10.2 解码等价测试

将两条链路输出的 payload 依次传入同一 `EEGPacketDecoder`，逐项验证：

- 解码帧数量完全相同；
- 每帧通道数完全相同；
- 每个通道采样值逐点相同；
- 帧顺序相同；
- 解码器剩余缓冲区相同；
- 半包、粘包和非法数据处理结果相同。

### 10.3 推理等价测试

同一录制数据经过完整链路后验证：

- EEG 窗口数量相同；
- 窗口边界相同；
- 特征矩阵相同；
- selected features 相同；
- scaler 输入和输出相同；
- 分类标签相同；
- 分类概率在预先定义的浮点容差内；
- 原始 `.npz` 内容和元数据语义相同。

### 10.4 真机测试

同一个 BLE EEG 设备通常不能同时连接 Windows 和 Linux 两个 client，因此采用顺序
测试：

1. 使用现有 Windows bridge 录制原始 JSONL；
2. 将录制文件输入容器 replay；
3. 比较 Redis 和模型输出；
4. 再由 Linux `eeg-bridge` 连接真机；
5. 验证扫描、连接、Notify、实时波形和模型推理；
6. 主动关闭设备并重新开启，验证自动重连；
7. 重启 Redis，验证错误可观测和恢复能力；
8. 连续运行至少 24 小时，检查丢包、内存、CPU 和重连次数。

## 11. 实施阶段

### 阶段一：冻结当前协议

- 为 `build_stream_entry` 建立字段快照测试；
- 为批处理建立边界测试；
- 为 Stream key 派生规则建立生产端/消费端一致性测试；
- 固定 payload encoding 为 `hex`；
- 固定首轮迁移的 `source` 值；
- 准备可重复使用的原始 EEG golden fixture。

退出条件：当前 Windows 链路的协议和行为已能通过自动化测试复现。

### 阶段二：完善容器运行能力

- 完善 `services/eeg-bridge/Dockerfile`；
- 完善 `docker-compose.jetson-eeg-bridge.yml`；
- 修正 `source` 字段兼容性；
- 增加 D-Bus socket 和 BlueZ 启动前检查；
- 增加不会因“设备未开机”而无限重启的 healthcheck；
- 明确 Redis 端口、认证和网络配置；
- 增加状态和录制数据卷；
- 提供 Linux 一键启动和停止命令。

退出条件：没有 EEG 设备时容器能够稳定扫描；设备开启后能够自动连接并发布数据。

### 阶段三：协议和结果等价验收

- 运行 golden fixture 对比；
- 运行解码逐点对比；
- 运行模型输入和输出对比；
- 验证蓝牙断线恢复；
- 验证 Redis 故障和恢复；
- 验证 bridge/replay 互斥；
- 完成真机连续稳定性测试。

退出条件：所有协议字段、原始字节、解码结果和模型结果达到本设计定义的等价标准。

### 阶段四：切换默认 Linux 部署

- Linux / Jetson 部署默认加载 EEG bridge overlay；
- 不再启动 Windows EXE 或宿主机 Python bridge；
- 暂时保留 Windows 工具作为回退；
- 保留 replay 用于测试和问题复现；
- 观察稳定运行周期后，再决定是否将 Windows bridge 标记为 legacy。

### 阶段五：非功能优化

必须在容器化验收完成后独立执行：

- 移除 `privileged: true`；
- 将 bridge 接入 Compose 内部网络；
- 镜像和依赖安全加固；
- Redis 失败消息重试或持久化缓冲；
- 指标采集与告警；
- 自动清理原始录制文件。

## 12. 验收标准

### 12.1 协议兼容

- Stream key 完全相同；
- Redis Entry 字段和编码完全相同；
- BLE 原始字节逐字节相同；
- batch 拼接顺序和边界相同；
- 下游不增加容器专属协议分支；
- 解码结果逐点相同；
- 模型标签相同，概率满足浮点容差。

### 12.2 功能

- 单条 Compose 命令可以启动业务和 bridge；
- EEG 设备开启后可以自动发现和连接；
- 能持续接收 Notify 并写入 Redis；
- 前端显示实时 EEG 波形；
- EEG 窗口能够完成推理和入库；
- 蓝牙断线后能够自动重连；
- bridge 和 replay 不会同时写入生产 Stream。

### 12.3 稳定性

- 连续运行至少 24 小时；
- 无持续内存增长；
- CPU 使用符合设备能力；
- 正常链路下 `dropped_packet_count=0`；
- Redis consumer lag 不持续增长；
- 无不可解释的窗口缺失或模型输入差异。

### 12.4 运维

- 能区分容器存活、BLE 连接和数据就绪；
- 状态文件和容器日志包含必要故障信息；
- 可以确认最后一次 BLE 接收和 Redis 发布时间；
- 可以查看累计接收、发布和丢包数量；
- 有明确的启动、停止、排障和回退步骤。

## 13. 风险与控制

| 风险 | 影响 | 控制措施 |
|---|---|---|
| Linux BlueZ 看不到设备 | bridge 持续扫描但无法连接 | 启动前检查 bluetoothd、rfkill、Controller 和宿主机扫描 |
| D-Bus 权限不足 | Bleak 扫描或连接报错 | 首轮保留 privileged；稳定后单独收缩权限 |
| 同一设备被其他 client 占用 | 连接失败或频繁断开 | 单实例约束，禁止 Windows bridge 与 Linux bridge 同时运行 |
| Stream key 配置不一致 | 生产正常但消费者无数据 | 对生产端和消费端派生规则建立自动化一致性测试 |
| payload 编码被改为 Base64 | 与既有协议不一致 | 显式固定 `EEG_HOST_BRIDGE_PAYLOAD_ENCODING=hex` |
| `source` 值变化 | 严格协议对比失败 | 首轮继续使用 `windows_host_bridge` |
| 修改 batch 参数 | 消息边界和时序变化 | 冻结 batch size=32、timeout=20ms |
| Redis 故障时丢 batch | EEG 窗口数据不完整 | 首轮保留既有行为并告警；可靠性改造单独设计 |
| 健康检查过严 | 设备未开机时容器重启循环 | 存活、连接、就绪三类状态分离 |
| 录制文件占满磁盘 | bridge 或主机异常 | 默认关闭录制，启用时设置容量与保留策略 |

## 14. 最终结论

推荐的正式形态为：

```text
独立 eeg-bridge 容器
  + Linux 宿主机 BlueZ / bluetoothd
  + system D-Bus socket
  + Redis Stream
  + 独立 multimodal-service
```

现有仓库已经具备 Dockerfile、Linux Compose overlay、Bleak BLE client、Redis
Stream writer、自动重连、状态文件和下游 Redis consumer，实施重点不是重写采集
程序，而是冻结协议、补齐容器运行保障，并完成宿主机链路与容器链路的字节级等价
验收。

在协议等价验收完成前，不修改 BLE 数据、Redis Entry、批处理边界、解码器、特征
工程或 EEG 模型。这样可以在取消 Windows 外接程序的同时，把对现有 EEG 数据链和
推理结果的影响控制到最低。
