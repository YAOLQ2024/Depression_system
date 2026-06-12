# 多模态文件命名与测试前清理改造方案

更新时间：2026-05-22

适用仓库：`depression-system`

---

## 1. 文档目标

本文档只解决一个问题：

**在进入下一轮真实测试之前，先对多模态相关文件做一轮“命名梳理 + 冗余清理 + 测试前收口”的工程化整理。**

本文档明确不做两件事：

- 不直接修改业务代码实现
- 不在本轮就做大规模目录迁移或删历史迁移文件

当前目标是先把事情想清楚、命名定清楚、清理边界定清楚，再进入下一步实际改造。

---

## 2. 当前问题判断

结合当前仓库结构，问题主要有 4 类。

### 2.1 文档目录命名不统一

当前多模态专项文档集中在：

- `docs/multiEmo/`

这个目录名有几个问题：

- 使用缩写，语义不完整
- 和仓库里大量英文全称命名风格不一致
- 新同学第一次看不容易判断这是“多模态工程文档目录”

从工程可维护性看，`multiEmo` 不如 `multimodal` 清晰。

### 2.2 部分文件名偏“讨论稿”风格，不够工程化

当前文档文件里，以下命名不够理想：

- `four-modality-integration-master-plan.md`
- `visual-modality-dedup-refactor-plan.md`
- `face-emotion-integration-plan.md`
- `pose-emotion-integration-plan.md`
- `speech-emotion-integration-plan.md`
- `text-emotion-integration-plan.md`

主要问题：

- `master` 偏口语，不如 `overview` 或 `integration` 明确
- `emotion` 和 `modality` 的边界有时混在一起
- 同类文件没有统一命名模板

### 2.3 `non_eeg_*` 这组代码命名是当前最不合理的一组

当前实际文件包括：

- `services/multimodal-service/app/api/non_eeg_inference.py`
- `services/multimodal-service/app/services/non_eeg_inference.py`
- `services/multimodal-service/app/services/non_eeg_runtime.py`
- `services/multimodal-service/tests/test_non_eeg_routes.py`

这组命名的问题最明显：

- 它是“用排除法命名”的：`non_eeg`
- 现在文件实际已经承载 `text / audio / face / pose`
- 从长期看，`non_eeg` 不是业务能力名，而是历史阶段名

这类名字在初期可以凑合，但到了现在已经会影响理解和扩展。

### 2.4 冗余文件和测试前噪音已经开始积累

目前比较值得注意的点：

- `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md`
  - 带日期后缀，更像阶段性草稿
  - 和当前 `docs/multiEmo/` 下的新方案存在潜在重叠
- `services/consultation-service/alembic/versions/20260519_0006_create_speech_emotion_results.py`
- `services/consultation-service/alembic/versions/20260519_0010_drop_speech_emotion_results.py`
  - 这是历史迁移痕迹，不建议现在删除，但需要明确“不纳入本轮清理”
- 多个 `__pycache__`
  - 属于本地运行产物，不应进入“业务文件”视角

---

## 3. 本轮命名设计原则

这轮我建议遵守 5 条简单规则。

### 3.1 目录用全称，不用缩写

建议：

- `multiEmo` -> `multimodal`

### 3.2 文件名优先体现“对象 + 作用”

例如：

- `face-integration-plan.md`
- `storage-db-design-plan.md`
- `legacy-modality-routes.py`

而不是：

- `master-plan`
- `multiEmo`
- `non_eeg`

### 3.3 同类文件采用同一模板

建议多模态文档统一模板：

- `<topic>-plan.md`
- `<topic>-design.md`
- `<topic>-checklist.md`

模态专项文档统一模板：

- `<modality>-integration-plan.md`

### 3.4 历史兼容层要直接写成 `legacy`

如果某文件的主要职责是兼容旧接口，就不要继续用抽象或绕弯的词。

建议：

- `non_eeg_inference.py` -> `legacy_modality_routes.py` 或 `legacy_modality_inference.py`

### 3.5 测试脚本命名要和测试对象一致

脚本名应该让人一眼看出：

- 是多模态相关
- 是哪个模态
- 是检查脚本

---

## 4. 建议的新命名方案

本节只给方案，不在本轮直接改。

### 4.1 文档目录

建议：

- `docs/multiEmo/` -> `docs/multimodal/`

原因：

- 语义完整
- 可搜索性更好
- 与 `multimodal-service` 保持一致

### 4.2 多模态文档文件

建议映射如下：

- `face-emotion-integration-plan.md` -> `face-integration-plan.md`
- `pose-emotion-integration-plan.md` -> `pose-integration-plan.md`
- `speech-emotion-integration-plan.md` -> `speech-integration-plan.md`
- `text-emotion-integration-plan.md` -> `text-integration-plan.md`
- `four-modality-integration-master-plan.md` -> `integration-overview-plan.md`
- `multimodal-storage-and-db-design-plan.md` -> `storage-db-design-plan.md`
- `visual-modality-dedup-refactor-plan.md` -> `visual-cleanup-plan.md`
- `multimodal-file-naming-and-cleanup-plan.md` -> 保持不变，或后续简化为 `file-naming-cleanup-plan.md`

说明：

- 如果目录已经改成 `docs/multimodal/`，文件名就没必要重复写 `multimodal`
- 文件名应短，但不能失去语义

### 4.3 旧文档与阶段性草稿

你当前已经明确了处理原则：

- **旧文档与阶段性草稿直接删除**
- **不进入 `archive/`**

在这个前提下，候选清理对象首先包括：

- `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md`

处理前提建议仍然保留一条：

- 先做一次“是否仍被 README、其他文档或脚本引用”的检查

只要确认已经被新文档完全替代，就直接删除，不再保留归档副本。

### 4.4 `multimodal-service` 代码文件

建议映射如下：

- `app/api/non_eeg_inference.py`
  - 建议改为：`app/api/legacy_modality_routes.py`
- `app/services/non_eeg_inference.py`
  - 建议改为：`app/services/modality_inference_service.py`
- `app/services/non_eeg_runtime.py`
  - 建议改为：`app/services/modality_runtime.py`
- `tests/test_non_eeg_routes.py`
  - 建议改为：`tests/test_legacy_modality_routes.py`

这样改的好处：

- 把“历史兼容层”和“当前能力层”分开
- 不再使用 `non_eeg` 这种排除式命名
- 新人能直接看懂文件职责

### 4.5 测试脚本命名

当前曾存在两个人脸 / 姿态模态检查脚本。

这两个名字不算错误，但顺序略别扭。

建议后续统一成：

- `run_multimodal_face_checks.ps1`
- `run_multimodal_pose_checks.ps1`

或者下一阶段再进一步统一成一个参数化脚本：

- `run_multimodal_checks.ps1 -Modality face`
- `run_multimodal_checks.ps1 -Modality pose`

本轮更推荐前者，风险小。

---

## 5. 冗余文件、历史文件、临时文件的处理策略

### 5.1 可以优先清理的

- 本地 `__pycache__/`
- 本地测试生成物
- 前端 `dist/` 这类构建产物

前提：

- 已确认不纳入版本控制
- `.gitignore` 已覆盖

### 5.2 可以直接删除的

- 旧的阶段性执行文档
- 被新文档完全替代的时间戳草稿

建议动作：

1. 先做“是否仍被引用”检查
2. 确认已被新文档完全替代
3. 直接删除，不保留 `archive/`

#### 建议直接删除的旧文档 / 阶段性草稿候选清单

下面这批文件建议作为“优先盘点并直接删除”的候选对象：

1. `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md`
   - 判断：高优先级删除候选
   - 原因：带日期后缀，明显是阶段性执行稿；当前已经有 `docs/multiEmo/` 下的多份新版专项方案承接同类内容
   - 当前状态：在仓库内未发现其他文件继续引用它

2. `docs/multiEmo/four-modality-integration-master-plan.md`
   - 判断：中高优先级删除候选
   - 原因：如果后续改名为更工程化的 `integration-overview-plan.md`，旧文件名本身就不应继续保留
   - 当前状态：更适合“重命名替代”，而不是旧名和新名并存

3. `docs/multiEmo/visual-modality-dedup-refactor-plan.md`
   - 判断：中高优先级删除候选
   - 原因：如果后续改名为 `visual-cleanup-plan.md`，旧文件名应直接退出，避免同一文档出现两份命名版本
   - 当前状态：更适合“重命名替代”，而不是复制出第二份

4. 后续重命名产生的旧文件名副本
   - 判断：一律直接删除
   - 范围包括：
     - `face-emotion-integration-plan.md`
     - `pose-emotion-integration-plan.md`
     - `speech-emotion-integration-plan.md`
     - `text-emotion-integration-plan.md`
   - 原因：如果后续统一改成 `<modality>-integration-plan.md`，那旧名字不应残留为第二份文件
   - 当前状态：这类文件不是“现在就删”，而是“重命名完成后，旧名字不得保留副本”

5. 本地运行产物对应的临时文档或检查草稿
   - 判断：发现即删
   - 范围：人工排查中若出现仅用于一次性验证、且未纳入正式方案体系的临时 `.md` 草稿
   - 原因：这类文件最容易污染目录结构，且对真实测试没有持续价值

这份候选清单里需要特别区分两类：

- `直接删除型`
  - 典型是 `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md`
- `重命名替代型`
  - 典型是 `four-modality-integration-master-plan.md`、`visual-modality-dedup-refactor-plan.md`、以及 4 个模态专项方案

也就是说，后者不是“先复制一份新名字再保留旧名字”，而是：

1. 完成重命名
2. 更新引用
3. 旧名字立即退出

### 5.3 当前不建议动的

- Alembic 历史迁移文件
- 仍有兼容调用价值的 legacy API 文件
- 已在脚本或 README 中稳定使用的回归入口

特别是这两份迁移：

- `20260519_0006_create_speech_emotion_results.py`
- `20260519_0010_drop_speech_emotion_results.py`

虽然从“故事线”上看冗余，但它们属于迁移历史，不应在这一轮为“干净”而硬删。

---

## 6. 测试前建议的清理顺序

我建议测试前按下面顺序推进。

### Phase 1：命名冻结

目标：

- 先确定今后的统一命名模板

输出：

- 目录名是否从 `multiEmo` 改为 `multimodal`
- 文档命名模板
- 服务代码命名模板
- 测试脚本命名模板

### Phase 2：文档层清理

目标：

- 先整理文档，不碰业务逻辑

建议动作：

- 重命名 `docs/multiEmo/` 下专项文档
- 检查旧执行稿是否仍被引用
- 对确认废弃的旧稿直接删除

### Phase 3：代码文件命名清理

目标：

- 处理最不合理的 `non_eeg_*`

建议动作：

- 先盘点调用入口
- 再改 API / service / test 文件名
- 同步修 import 和 README

注意：

- 这一步一定放在文档清理之后
- 不建议和业务逻辑改动混做

### Phase 4：本地噪音清理

目标：

- 清掉不该干扰测试视角的本地产物

建议动作：

- 删除 `__pycache__`
- 清理本地构建产物
- 检查 `.gitignore`

### Phase 5：测试前最终收口

目标：

- 确保进入真实测试时，仓库结构已经足够清楚

建议动作：

- 再跑一遍 `face/pose` 最小回归
- 检查 README 是否还引用旧文件名
- 检查是否存在“文档写新名字、代码还是旧名字”的断裂

---

## 7. 本轮不建议做的事

### 7.1 不建议一边重命名一边继续加新功能

原因：

- 容易把“命名清理问题”和“功能回归问题”混在一起

### 7.2 不建议现在就深拆 `modality_inference_service`

虽然长期看可以按 `audio / text / face / pose` 继续拆，但在真正测试前，先把名字改对更重要。

### 7.3 不建议把历史迁移、兼容路由、回归脚本一次性大扫除

这类清理最容易“看起来很干净，实际把回归入口删没了”。

---

## 8. 推荐先做的 10 个具体动作

1. 确认 `docs/multiEmo/` 是否整体迁为 `docs/multimodal/`
2. 统一模态专项文档命名为 `<modality>-integration-plan.md`
3. 把 `four-modality-integration-master-plan.md` 改成 `integration-overview-plan.md`
4. 把 `visual-modality-dedup-refactor-plan.md` 改成 `visual-cleanup-plan.md`
5. 盘点 `docs/apps/consultation/four-modality-integration-execution-plan_20260517.md` 是否仍被引用，并在确认废弃后直接删除
6. 把 `app/api/non_eeg_inference.py` 列为首要重命名对象
7. 把 `app/services/non_eeg_inference.py` 和 `app/services/non_eeg_runtime.py` 列为第二批重命名对象
8. 把 `tests/test_non_eeg_routes.py` 改成直接反映 legacy 路由职责的名字
9. 清理本地 `__pycache__` 和构建产物
10. 在正式测试前做一次“旧名字引用扫描”

---

## 9. 最终结论

当前多模态相关文件最大的问题不是功能跑不通，而是：

- 命名开始带有历史阶段痕迹
- 部分文档名不够工程化
- `non_eeg_*` 这组文件已经明显落后于当前职责
- 旧草稿、兼容层、本地产物开始混在一起

因此，在下一步真实测试前，最合适的动作不是继续加功能，而是先完成一轮：

**“命名冻结 -> 文档整理 -> 代码文件重命名 -> 本地噪音清理 -> 测试前收口”**

这样后面的真实测试、问题定位和后续论文整理都会更稳。
