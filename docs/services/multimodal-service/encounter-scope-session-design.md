# Encounter 作用域多模态会话设计

## 目标

将 `multimodal_session` 从“单个 flow 作用域”调整为“单个 encounter 作用域”，让数字人问诊和量表问诊在同一次 `encounter_session` 内共用同一条连续多模态链。

## 目标契约

- 一个 `encounter_session` 只绑定一个 `multimodal_session`
- `consultation` 和 `assessment` 都复用这个 `multimodal_session_id`
- 流程归属从 session 层下沉到 turn/capture/bundle 层

## 会话作用域

新增 session 级字段：

- `scope_type`
  - 第一阶段支持 `encounter` 和兼容值 `flow`
- `scope_id`
  - 当 `scope_type=encounter` 时，值为 `encounter_session_id`

兼容策略：

- 旧逻辑仍保留 `flow_type + flow_run_id`
- 新创建的 consultation multimodal session 改为：
  - `scope_type=encounter`
  - `scope_id=encounter_session_id`
  - 同时保留 `flow_type=consultation`
  - 同时保留 `flow_run_id=consultation_session_id`

这样可以在不打断旧链路的前提下，把 session 唯一性切到 `encounter`。

## Turn 元数据

第一阶段先补充：

- `origin_flow_type`
  - `consultation` 或 `assessment`

兼容约定：

- 现有 turn/capture/bundle 表里的 `flow_run_id` 暂时继续承担 `origin_flow_run_id` 的职责
- 等 consultation/assessment 全面切换稳定后，再决定是否补一轮显式重命名迁移

## 校验变更

旧校验：

- `multimodal_session.flow_run_id` 必须等于上传请求中的 `flow_run_id`

新校验：

- 如果 session 是旧的 `flow` 作用域，继续执行旧校验
- 如果 session 是新的 `encounter` 作用域，不再用 session-level `flow_run_id` 拦截上传
- `flow_run_id` 继续要求存在，但语义变为“当前 turn 的 origin flow run id”

## 迁移计划

### 阶段一

- `multimodal-service`
  - 新增 `scope_type / scope_id`
  - 新增 `origin_flow_type`
  - 放宽 `encounter` 作用域 session 的 `flow_run_id` 校验
  - API 保持向后兼容

### 阶段二

- `consultation-service`
  - 创建 consultation 时，按 `encounter` 作用域创建 multimodal session
  - 继续返回同一个 `multimodal_session_id`

### 阶段三

- `assessment-service`
  - 创建 assessment session 时不再新建 multimodal session
  - 复用 consultation 已有的 `multimodal_session_id`
  - assessment turn 上传时，`origin_flow_type=assessment`

### 阶段四

- 前端
  - 量表页不再 `createMultimodalSession`
  - 直接复用 consultation 阶段的 `multimodal_session_id`
  - SSE/live/finalize/recover 全部挂到同一 session

## 当前增量

本轮先做 `Phase 1 + Phase 2`，让底层 session scope 和 consultation 创建口径先稳定下来，再做 assessment 复用切换。
