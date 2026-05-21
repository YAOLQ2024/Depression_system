# 姿态、文本、面部、语音四模态接入/显示/存储执行方案

更新时间：2026-05-17

适用仓库：`depression-system`

适用范围：`consultation` 患者端正式问诊阶段的四模态能力接入、页面显示、数据存储与接口编排

---

## 1. 这份方案基于哪些“最相关/最新”的文档与代码

这次执行方案不是凭空设计，主要依据当前仓库中这几份最相关文档和现状代码：

### 1.1 最相关且最新的主文档

1. `docs/apps/consultation/digital-human-consultation-step4-design.md`
   - 当前与“四阶段数字人问诊 + 多模态接入”最直接相关的主设计文档
   - 已经把视频问诊、语音回答、ASR、多模态持续运行、turn 绑定、对象存储等主链约束写清楚

2. `docs/MCS_API与模块协调汇报稿_20260513.md`
   - 当前全系统接口、模块边界、服务协同状态的最新汇总
   - 明确指出 `multimodal-service` 仍未实现，只完成了接口边界定义

3. `docs/services/multimodal-service/api-and-data.md`
   - 多模态服务的核心接口和数据实体草案
   - 已包含 `multimodal_session`、`multimodal_capture`、`multimodal_feature_bundle` 的基本概念

4. `docs/services/multimodal-service/tasks.md`
   - 当前多模态服务实施任务与 owner 分工
   - 明确了“先定统一输出格式，再逐个接真实模态”的策略

5. `docs/apps/consultation/backend-integration-plan.md`
   - 当前患者端从 mock 切真实接口的总计划
   - 其中 Step 4 已经定义了数字人问诊页的主接线顺序

### 1.2 必须参考的现状代码

1. `apps/consultation/client/src/pages/ConsultationPage.tsx`
   - 当前数字人问诊页已经有：
     - 固定视频播放位
     - 浏览器录音
     - 问答窗口时间戳
     - `submitConsultationTurn()` 提交入口
   - 但还没有真正把四模态结果接进来

2. `apps/consultation/client/src/components/MultimodalPanel.tsx`
   - 当前右侧多模态面板仍然是 mock 展示
   - 摄像头、表情、姿态、语音、EEG、文本分析都还是假数据

3. `apps/consultation/client/src/services/api/contracts.ts`
   - 当前前端真实接口契约里还没有四模态专用请求/响应类型

4. `apps/consultation/client/src/types.ts`
   - 当前 `ConsultationSession` 已经预留了：
     - `current_question_key`
     - `current_question_video_uri`
     - `current_question_item`
   - 说明问诊主链已经具备绑定“当前题目”的基础

5. `apps/consultation/client/src/types/consultation.ts`
   - 当前 `MultimodalData` 仍是旧 prototype mock 类型
   - 不适合继续作为真实四模态接口契约

6. `services/multimodal-service/app/main.py`
   - 当前只有 `/health/live` 与 `/health/ready`
   - 说明多模态服务几乎还是纯骨架，主接口、模型调用、持久化都需要正式补齐

7. `docs/database-tables/consultation_turns.md`
   - 已经明确 `consultation_turns` 应保存：
     - `prompt_key`
     - `prompt_question_text`
     - `response_started_at`
     - `response_completed_at`
     - `transcript_text`
   - 这为四模态结果按 turn 绑定提供了现成落点

---

## 2. 当前项目真实现状判断

结论先说：

- 问诊页主链已经有“视频 + 回答窗口 + 录音 + 提交 turn”的基础
- 四模态显示层已经有面板位置，但现在几乎全是假数据
- 四模态服务目前还没有真正实现
- 数据库层已经有 `consultation_turns` 作为问答绑定主轴，但还缺多模态专属表

### 2.1 已经具备的基础

1. 数字人问诊会话可以按 `consultation session` 组织
2. 当前题目可以按 `prompt_key / question_item` 定位
3. 回答窗口可以记录 `response_started_at / response_completed_at`
4. 浏览器可以本地录音
5. 问诊页右侧已经有多模态看板位置

### 2.2 当前最大的缺口

1. `multimodal-service` 没有会话接口
2. 没有真实的语音转写/语音情绪/文本情绪/face/pose 接入接口
3. 没有多模态统一返回结构
4. 没有“turn 级结果包”落库
5. 问诊页没有消费真实四模态结果
6. 当前 mock `MultimodalData` 类型会误导后续开发

---

## 3. 这次执行范围要刻意收窄

这次先只做 4 个模态：

1. 语音
2. 文本
3. 面部
4. 姿态

本轮明确**不把 EEG 混进第一阶段实现**，原因：

- 你这次明确提的是 4 个模态
- EEG 在当前文档里有独立 owner、设备链路和外部 FastAPI 依赖
- 如果把 EEG 一起拉进第一阶段，开发和联调面会明显失控

所以建议把当前总目标拆成：

- Phase 1：姿态 + 文本 + 面部 + 语音
- Phase 2：EEG 接入并并入统一 bundle

---

## 4. 四模态的产品目标

本轮完成后，问诊页应具备下面 3 类能力：

### 4.1 接入

- 每一轮回答结束后，后端能得到：
  - 原始音频
  - ASR 转写文本
  - 语音情绪识别结果
  - 文本情绪识别结果
  - 回答窗口内的面部聚合结果
  - 回答窗口内的姿态聚合结果

### 4.2 显示

问诊页右侧多模态看板至少显示真实：

- 摄像头预览
- 当前语音情绪
- 当前文本情绪
- 当前面部主情绪
- 当前姿态主状态/主情绪

并且这些结果必须来自当前问诊会话的真实数据，而不是随机数或 mock 文案。

### 4.3 存储

每一轮回答都必须能回溯：

- 用户回答的是哪一道题
- 对应哪段原始音频
- ASR 转写是什么
- 语音情绪是什么
- 文本情绪是什么
- 当前回答窗口内的 face / pose 汇总是什么

---

## 5. 建议的数据绑定原则

四模态所有结果都必须至少绑定下面 4 个字段：

- `consultation_session_id`
- `consultation_turn_id`
- `prompt_key`
- `window_started_at / window_ended_at`

这是这次方案最重要的技术约束。

如果这 4 个字段没有固定住，后面一定会出现：

- 语音结果串到别的问题
- face / pose 结果无法和当前问题对齐
- 只能看“某场会话大概有结果”，但无法精确回放“某一题的多模态状态”

---

## 6. 建议的接口方案

浏览器仍然只访问 `gateway-service`。

### 6.1 浏览器 -> 网关

建议新增或补齐：

1. `POST /api/v1/consultations/{session_id}/turns/audio-answer`
   - 提交一轮完整语音回答
   - 建议请求体：
     - `prompt_key`
     - `response_started_at`
     - `response_completed_at`
     - `audio_blob`（multipart）

2. `POST /api/v1/consultations/{session_id}/captures/face`
   - 提交本轮回答窗口内抽样帧或帧引用

3. `POST /api/v1/consultations/{session_id}/captures/pose`
   - 提交本轮回答窗口内抽样帧或帧引用

4. `GET /api/v1/consultations/{session_id}/multimodal/live`
   - 获取当前会话最新四模态实时状态

5. `GET /api/v1/consultations/{session_id}/multimodal/turns/{turn_id}/bundle`
   - 获取某一轮回答的四模态结果包

### 6.2 网关 -> multimodal-service

建议内部接口统一收口为：

1. `POST /api/v1/multimodal/sessions`
2. `GET /api/v1/multimodal/sessions/{session_id}`
3. `POST /api/v1/multimodal/sessions/{session_id}/warmup`
4. `POST /api/v1/multimodal/sessions/{session_id}/audio-turns`
5. `POST /api/v1/multimodal/sessions/{session_id}/captures/face`
6. `POST /api/v1/multimodal/sessions/{session_id}/captures/pose`
7. `GET /api/v1/multimodal/sessions/{session_id}/live`
8. `GET /api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle`

---

## 7. 建议的数据库与对象存储方案

### 7.1 继续沿用 `consultation_turns` 做问答主轴

`consultation_turns` 继续保存：

- `prompt_key`
- `prompt_question_text`
- `response_started_at`
- `response_completed_at`
- `transcript_text`

这张表不负责装全部模态细节，但它必须成为所有模态结果的“题目绑定主轴”。

### 7.2 在 `multimodal-service` 新增 4 张表

#### 表 1：`multimodal_sessions`

- `id`
- `owner_service`
- `owner_session_id`
- `user_id`
- `status`
- `warmup_status`
- `started_at`
- `updated_at`

#### 表 2：`multimodal_captures`

- `id`
- `session_id`
- `consultation_turn_id`
- `modality` (`speech` / `face` / `pose`)
- `capture_kind`
- `source_uri`
- `capture_started_at`
- `capture_ended_at`
- `processing_status`
- `quality_flags`

#### 表 3：`multimodal_inference_results`

- `id`
- `session_id`
- `consultation_turn_id`
- `capture_id`
- `modality`
- `model_name`
- `model_version`
- `label`
- `score`
- `result_payload`
- `window_started_at`
- `window_ended_at`
- `created_at`

#### 表 4：`multimodal_turn_bundles`

- `id`
- `session_id`
- `consultation_turn_id`
- `prompt_key`
- `transcript_text`
- `speech_emotion_summary`
- `text_emotion_summary`
- `face_summary`
- `pose_summary`
- `quality_flags`
- `generated_at`

### 7.3 哪些数据进对象存储

必须进对象存储：

- 原始回答音频
- 可选调试留样帧

不建议直接塞 PostgreSQL：

- 完整原始音频二进制
- 连续视频帧流

---

## 8. 页面显示方案

### 8.1 先保留右侧多模态面板位置

不建议这轮先重做 UI 结构，原因是：

- 现有 `ConsultationPage.tsx` 已经有右侧结果看板抽屉
- 问题不是位置不够，而是数据全是假

所以这一轮页面策略是：

- 保留现有面板结构
- 把 `MultimodalPanel.tsx` 从 mock 数据面板改成真实数据面板

### 8.2 面板第一版只显示 5 类真实结果

第一版建议只显示：

1. 摄像头预览
2. 语音情绪：主标签 + 分数
3. 文本情绪：主标签 + 分数
4. 面部：主标签 + 分数
5. 姿态：主标签 + 分数

先不要显示：

- 花哨波形随机动画
- 假 EEG 图
- 虚构标签云
- 无法解释的二级指标

---

## 9. 当前最合理的实施顺序

## Step A：先定统一契约，不写模型逻辑

目标：

- 把 4 模态统一返回结构定下来
- 把前端 mock 类型替换成真实契约类型

要做：

1. 在 `docs/services/multimodal-service/api-and-data.md` 补齐四模态统一 schema
2. 在 `apps/consultation/client/src/services/api/contracts.ts` 增加：
   - `MultimodalLiveResponse`
   - `MultimodalTurnBundleResponse`
   - `CreateMultimodalSessionPayload`
3. 新建 `client/src/types/multimodal.ts`
4. 停止继续使用 `client/src/types/consultation.ts` 中旧 `MultimodalData`

验收：

- 前后端都只认一套四模态字段结构

## Step B：先把服务骨架补起来，返回占位真结构

目标：

- `multimodal-service` 不再只有 health
- 即使模型还没全接，也要先返回稳定的真结构

要做：

1. 新增 `app/api/multimodal.py`
2. 新增会话、live、turn bundle 路由
3. 新增 `schemas/` 和 `services/` 的基础数据结构
4. 先返回结构化占位数据，不直接上模型

验收：

- 网关能调用 `multimodal-service`
- 前端能拿到真实字段结构

## Step C：先打通语音与文本这条最短链路

目标：

- 先让“录音 -> ASR -> 文本情绪 -> 语音情绪 -> turn bundle”这条线跑通

要做：

1. `ConsultationPage.tsx` 录音结束后，走 `audio-answer` 接口
2. `multimodal-service` 保存音频到对象存储
3. 跑：
   - ASR
   - Speech Emotion
   - Text Emotion
4. 结果写：
   - `consultation_turns.transcript_text`
   - `multimodal_inference_results`
   - `multimodal_turn_bundles`

验收：

- 一道题结束后，页面能看到真实语音情绪和文本情绪

## Step D：接通 face 与 pose

目标：

- 让摄像头采样、面部推理、姿态推理跑通

要做：

1. 前端在回答窗口内采样
2. `captures/face` 与 `captures/pose` 入后端
3. 后端推理并记录细粒度结果
4. 每轮回答结束时生成：
   - `face_summary`
   - `pose_summary`

验收：

- 一道题结束后，页面能看到真实面部和姿态结果

## Step E：把面板从 mock 改成真实读接口

目标：

- `MultimodalPanel.tsx` 不再读假数据

要做：

1. 去掉随机文案、随机波形、假标签
2. 改为消费：
   - `GET /multimodal/live`
   - `GET /multimodal/turns/{turn_id}/bundle`
3. 用真实空态、加载态、错误态替代假展示

验收：

- 问诊页右侧面板只展示真实结构化结果

## Step F：最后清理旧 mock 类型和旧假数据

目标：

- 把旧 prototype 残留清掉

要做：

1. 清理 `types/consultation.ts` 中旧 `MultimodalData`
2. 清理 `MultimodalPanel.tsx` 中假的：
   - EEG 波形
   - 文本分析标签云
   - 表情/姿态硬编码文案
3. 清理所有“正常/稳定 92%/平静 76%”这类假状态

验收：

- 四模态页面只剩真实数据或真实空态

---

## 10. 我建议你现在立刻按这个顺序推进

如果我们要尽快开始，不建议同时动 20 个点。最稳的起手顺序是：

1. 先改文档契约
2. 再补 `multimodal-service` 的 API 骨架
3. 先打通语音 + 文本
4. 再接 face + pose
5. 最后改前端显示和清 mock

原因很现实：

- 语音 + 文本是最短闭环
- face + pose 要多一步前端采样和窗口聚合
- 如果一开始就四模态一起上，排错会很痛苦

---

## 11. 当前建议结论

对这个项目来说，当前最相关、最值得作为主依据的文档就是：

1. `digital-human-consultation-step4-design.md`
2. `MCS_API与模块协调汇报稿_20260513.md`
3. `multimodal-service/api-and-data.md`

它们共同说明了一件事：

- 主流程和页面位置已经定了
- 多模态边界已经定了
- 当前真正缺的是“四模态统一契约 + 多模态服务实现 + 前端面板去假数据”

所以这次执行方案不应该再泛泛谈“以后可以接模型”，而应该进入：

- 先定契约
- 先补骨架接口
- 先跑语音文本闭环
- 再接 face / pose
- 最后替换显示层

