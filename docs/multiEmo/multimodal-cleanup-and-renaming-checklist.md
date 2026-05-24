# 多模态清理与命名收口检查清单

更新时间：2026-05-23

适用仓库：`depression-system`

---

## 1. 文档目标

本文档用于回答一个当前最实际的问题：

**在 `visual-captures` 新主链已经落地、`face/pose` 外部旧上传接口已经删除之后，下一步如何系统性完成多模态相关的废弃代码、历史文档、命名不清文件和本地噪音的清理收口。**

本文档不做两件事：

- 不继续推进新的多模态功能
- 不在本轮直接修改模型本身

当前目标是先把仓库结构、命名、历史痕迹和说明口径收干净，再进入下一轮稳定测试或后续架构收敛。

---

## 2. 当前状态判断

结合当前仓库实际情况，当前多模态工程已经进入“功能基本成形，但仓库认知噪音偏多”的阶段。

已完成的关键事实：

- 外部视觉主链已经切换为：
  - `/consultations/{session_id}/multimodal/visual-captures`
  - `/api/v1/multimodal/sessions/{session_id}/visual-captures`
- 旧外部上传路径已经删除：
  - `captures/face`
  - `captures/pose`
  - `captures/visual`
- `face/pose` 仍作为后端内部 fan-out 子流程存在
- `pose` 当前已确认更适合作为实验性辅助模态

当前最突出的问题不再是“链路能不能跑”，而是：

- 旧文档仍大量引用已删除的接口
- `non_eeg_*` 仍在核心代码路径中
- `docs/multiEmo/` 目录名与文件名不够工程化
- 本地和历史阶段性文件对后续维护有干扰

---

## 3. 本轮收口目标

本轮建议只做 4 类事：

1. 删除确认废弃的旧文档与旧说明
2. 收口当前不够工程化的文件名与模块名
3. 清理与系统运行无关的本地噪音
4. 统一 README / 方案文档 / 当前代码之间的口径

本轮不建议做：

- 新一轮多模态功能开发
- 数据库结构重做
- pose 模型层面优化
- 业务逻辑和重命名大改混做

---

## 4. 检查清单总览

### 4.1 第一类：建议直接删除

以下内容优先做“是否仍被引用”检查；若无有效引用，建议直接删除。

#### A. 旧接口说明文档

- `docs/services/multimodal-service/api-and-data.md`
- `docs/services/multimodal-service/tasks.md`
- `docs/apps/consultation/digital-human-consultation-step4-design.md`
- `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md`
- `docs/apps/consultation/Step4D_其他非EEG接口规范_给刘倩_20260517.md`

删除理由：

- 仍大量描述已删除的 `captures/face`、`captures/pose`
- 容易误导后续联调和论文整理
- 已经被 `docs/multiEmo/` 下的新方案文档体系替代

#### B. 明显本地噪音

- `__pycache__/`
- `*.pyc`
- 前端构建产物
- 一次性测试输出文件

处理原则：

- 不进入版本控制
- 如果已存在本地工作区，直接清掉

### 4.2 第二类：建议重命名

#### A. 文档目录

- `docs/multiEmo/` -> `docs/multimodal/`

理由：

- `multiEmo` 是阶段性缩写，不如 `multimodal` 清晰
- 与 `multimodal-service` 命名风格一致

#### B. 文档文件

建议新命名：

- `four-modality-integration-master-plan.md` -> `integration-overview-plan.md`
- `visual-modality-dedup-refactor-plan.md` -> `visual-cleanup-plan.md`
- `face-emotion-integration-plan.md` -> `face-integration-plan.md`
- `pose-emotion-integration-plan.md` -> `pose-integration-plan.md`
- `speech-emotion-integration-plan.md` -> `speech-integration-plan.md`
- `text-emotion-integration-plan.md` -> `text-integration-plan.md`

说明：

- 目录已经能表达“多模态”，文件名没必要再写长前缀
- `emotion` 不是每个文档都需要强调的主对象
- `master-plan` 不如 `overview-plan` 工程化

#### C. 代码模块

当前最需要处理的是这组：

- `services/multimodal-service/app/api/non_eeg_inference.py`
- `services/multimodal-service/app/services/non_eeg_inference.py`
- `services/multimodal-service/app/services/non_eeg_runtime.py`
- `services/multimodal-service/app/schemas/non_eeg.py`
- `services/multimodal-service/tests/test_non_eeg_routes.py`

建议命名方向：

- `app/api/non_eeg_inference.py`
  - -> `app/api/legacy_modality_routes.py`
  - 如果其主要职责已经不再是 legacy，可进一步评估为 `modality_inference_routes.py`
- `app/services/non_eeg_inference.py`
  - -> `app/services/modality_inference_service.py`
- `app/services/non_eeg_runtime.py`
  - -> `app/services/modality_runtime.py`
- `app/schemas/non_eeg.py`
  - -> `app/schemas/modality_inference.py`
- `tests/test_non_eeg_routes.py`
  - -> `tests/test_legacy_modality_routes.py`

当前判断重点：

- `non_eeg` 是历史阶段名，不是当前职责名
- 这组命名已经明显落后于现代码职责

### 4.3 第三类：建议保留，但要改说明

#### A. `visual-shared-input-refactor-plan.md`

建议保留，但需要后续收口：

- 删掉已完成阶段里不再需要的大量过程性表述
- 最终压缩成“当前结构 + 已完成项 + 剩余项”

#### B. `visual-sampling-and-live-tuning-plan.md`

建议保留，但保持当前真实值：

- `live = 5s`
- `visual-captures = 1.5s`

#### C. `pose-emotion-integration-plan.md`

建议保留，但当前必须明确：

- `pose` 当前为实验性辅助模态
- 不应在后续文档中继续被描述为“稳定正式模态”

### 4.4 第四类：当前不建议动

以下内容本轮不建议处理：

- Alembic 历史迁移文件
- `multimodal_visual_frames` 新数据层实体
- 已经工作正常的 `visual-captures` 主链
- 与语音主链直接相关的稳定接口

---

## 5. 推荐执行顺序

### Phase 1：旧文档与旧说明清理

目标：

- 先把最容易误导人的历史说明删掉

执行清单：

1. 扫描旧文档是否仍被 README 或其他新文档引用
2. 删除确认废弃的旧 Step4/旧 capture 文档
3. 再次扫描仓库内是否仍存在：
   - `captures/face`
   - `captures/pose`
   - `captures/visual`

完成标准：

- 仓库内不再有“仍在作为现状说明”的旧视觉上传路径文档

### Phase 2：文档目录与文件名收口

目标：

- 把 `docs/multiEmo/` 这一层先工程化

执行清单：

1. 确认目录整体迁移为 `docs/multimodal/`
2. 重命名 4 个模态专项方案
3. 重命名总方案与清理方案文档
4. 修正文档之间的互相引用

完成标准：

- 文档目录和文件名不再依赖缩写或口语化命名

### Phase 3：`non_eeg_*` 代码命名收口

目标：

- 处理当前最不工程化的一组代码命名

执行清单：

1. 先盘点导入关系
2. 重命名 API 层文件
3. 重命名 service 层文件
4. 重命名 schema 文件
5. 重命名相关测试文件
6. 同步修：
   - import
   - README
   - 文档引用

完成标准：

- 核心多模态代码路径不再使用 `non_eeg` 这类排除式历史命名

### Phase 4：本地噪音清理

目标：

- 清掉不属于系统正式工程资产的本地噪音

执行清单：

1. 清理 `__pycache__`
2. 清理 `.pyc`
3. 清理前端构建产物
4. 检查 `.gitignore` 是否覆盖

完成标准：

- 工作区里不再有明显运行产物污染视线

### Phase 5：最终收口验证

目标：

- 确保删改命名后，仓库仍可正常联调

执行清单：

1. 前端：
   - `npm run typecheck`
   - `npm run build`
2. Python 侧：
   - `python -m py_compile` 覆盖改动文件
3. 服务路由：
   - 核查 `visual-captures` 主链仍可达
4. 文档一致性：
   - README、方案、代码接口名一致

完成标准：

- “代码、文档、README、测试入口” 四处口径一致

---

## 6. 推荐先做的 12 个具体动作

1. 删除 `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md`
2. 删除 `docs/apps/consultation/Step4D_其他非EEG接口规范_给刘倩_20260517.md`
3. 删除或重写 `docs/apps/consultation/digital-human-consultation-step4-design.md`
4. 删除或重写 `docs/services/multimodal-service/api-and-data.md`
5. 删除或重写 `docs/services/multimodal-service/tasks.md`
6. 把 `docs/multiEmo/` 迁为 `docs/multimodal/`
7. 重命名 `four-modality-integration-master-plan.md`
8. 重命名 `visual-modality-dedup-refactor-plan.md`
9. 统一 `face/speech/text/pose` 四个专项方案名
10. 重命名 `app/api/non_eeg_inference.py`
11. 重命名 `app/services/non_eeg_inference.py`、`app/services/non_eeg_runtime.py`、`app/schemas/non_eeg.py`
12. 重命名 `tests/test_non_eeg_routes.py`

---

## 7. 推荐执行方案

### 方案 A：稳妥分两轮

第一轮：

- 只清旧文档
- 只清本地噪音
- 不改代码模块名

第二轮：

- 再改 `docs/multiEmo/`
- 再改 `non_eeg_*`

适用情况：

- 当前还在频繁联调
- 希望把回归风险压到最低

### 方案 B：当前最推荐

一轮内做完：

1. 旧文档清理
2. `docs/multiEmo/` 目录与文件名收口
3. `non_eeg_*` 代码命名收口
4. 最小回归验证

适用情况：

- 当前视觉主链已经稳定
- 已经不再依赖旧外部 capture 路由
- 团队准备进入更长期维护阶段

### 方案 C：激进一次性大扫除

不推荐。

原因：

- 容易把“删历史”和“功能回归”混在一起
- 一旦出错，不容易定位是命名问题还是功能问题

---

## 8. 我当前的推荐结论

从项目实际情况看，当前最合适的是：

**按方案 B 执行，但内部顺序必须固定为：**

1. 先删旧文档
2. 再改 `docs/multiEmo/`
3. 再改 `non_eeg_*`
4. 最后做一轮最小回归

也就是说，下一步不该继续围绕 `pose` 调参，也不该再做新功能，而应该先把：

**废弃代码、历史文档、命名不合理文件、运行产物噪音**

这四类问题收干净。

---

## 9. 最终验收口径

完成本轮收口后，应满足这 6 条：

1. 仓库内不再保留仍描述旧 `captures/face` / `captures/pose` 主链的现状文档
2. 文档目录和文件名不再依赖 `multiEmo` 缩写
3. 核心多模态代码路径不再使用 `non_eeg_*`
4. README 与当前接口命名一致
5. 前端和后端最小验证通过
6. 后续新同学仅看文件名，就能大致判断职责和阶段状态

