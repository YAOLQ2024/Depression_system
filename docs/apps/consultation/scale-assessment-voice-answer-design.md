# 量表问诊语音答题与自动选项推进设计

## 1. 目标

在当前已接通的量表视频预览基础上，把 `PHQ-9` 和 `SDS` 做成和数字人问诊一致的“视频播报 -> 用户回答 -> 自动推进”流程。

本次设计覆盖：

- 进入量表页后自动播放当前题目视频
- 视频播放完成后才允许回答
- 用户可通过两种方式答题
  - 方式 A：点击左侧量表看板选项
  - 方式 B：通过语音回答
- 语音回答结束后：
  - 字幕区显示最终 ASR 转写文本
  - 后端对转写文本做选项归一化
  - 自动选中左侧量表看板对应选项
  - 当前题答案落库
  - 原始音频、转写文本、多模态结果按当前题绑定
  - 自动推进到下一题并自动播放下一题视频

本次不做：

- `SAS`
- `社会功能缺陷量表`
- 量表结果页展示优化
- 复杂重答/回退题目

## 2. 现状

当前已经具备：

- 量表页可以按真实视频清单播放 `PHQ-9` 和 `SDS`
- 视频播完后才允许点击左侧选项
- 左侧量表看板、顶部阶段进度、右侧状态面板会随当前题同步变化
- `assessment-service` 已支持：
  - 创建量表会话
  - 获取量表会话
  - 提交单题答案
- 数字人问诊链路已支持：
  - 浏览器录音
  - 上传原始音频到 `multimodal-service`
  - Dolphin ASR
  - 字幕区显示转写
  - 语音/文本/表情/姿态多模态状态刷新

当前缺口：

- 量表页仍是前端本地预览推进，没有真实提交
- 量表语音回答还没有接入现有录音与 ASR 主链
- `assessment_answers` 当前只保存：
  - `raw_input`
  - `normalized_option`
  - `score_value`
  - `capture_timestamp`
- 还没有把原始音频 URI、最终转写文本、回答时间窗、turn 级标识保存到量表侧

## 3. 设计原则

- 最大化复用数字人问诊现有录音与多模态链路，不重新发明一套
- 量表题目也使用“题目窗口”语义，每一题都视作一个 turn
- 前端只负责采集与展示；选项归一化和自动选项判定放后端
- 点击选项和语音回答最终都走同一个量表答案提交入口
- 先做稳定可追踪的数据绑定，再做更复杂的语义理解增强

## 4. 用户流程

### 4.1 页面进入

1. 用户从数字人问诊 handoff 进入量表页
2. 前端加载或恢复 `assessment_session`
3. 前端根据 `assessment.current_scale_slug + current_item` 和 `scale-assessment-v1` 视频清单定位当前题
4. 自动播放当前题数字人视频

### 4.2 视频播放中

- 左侧量表选项全部禁用
- 底部录音按钮禁用
- 字幕区显示当前题数字人播报文本

### 4.3 视频播放完成后

- 左侧量表选项解禁
- 底部录音按钮解禁
- 用户可二选一：
  - 点击看板选项提交
  - 开始录音，用语音回答

### 4.4 点击看板选项

1. 前端拿到被选中的 `score` 与 `label`
2. 调用量表答案提交接口
3. 后端保存本题答案
4. 若还有下一题，返回更新后的 `assessment_session`
5. 前端切到下一题并自动播放下一题视频

### 4.5 语音回答

1. 用户点击“开始录音”
2. 前端复用数字人问诊现有浏览器录音逻辑
3. 用户点击“结束录音”
4. 前端上传原始音频到 `multimodal-service`
5. 等待 Dolphin 最终转写文本
6. 前端字幕区显示：
   - 数字人题干
   - 用户最终转写文本
7. 前端把最终转写文本发送给后端做选项归一化与语义判定
8. 后端先完成“转写文本 -> 标准选项文案/分值”的判定，再把标准选项作为最终答案写入量表答案主链
9. 后端返回：
    - 判定出的 `selected_option_label`
    - `selected_option_score`
    - 更新后的 `assessment_session`
10. 前端高亮左侧看板对应选项
11. 显示 800ms 的确认态
12. 自动推进到下一题并自动播放下一题视频

## 5. 复用数字人问诊现有能力

量表答题不应新造一套录音/ASR/多模态逻辑，直接复用现有问诊主链。

### 5.1 复用前端录音链

直接复用 `ConsultationPage.tsx` 中这些能力：

- 浏览器录音与权限处理
- `uploadMultimodalAudioTurn`
- `getMultimodalAudioTurn`
- 等待 Dolphin 最终转写
- 字幕区显示用户最终文本
- 多模态 live / bundle 刷新

### 5.2 复用多模态维度

量表语音答题继续采集：

- 原始音频
- ASR 转写
- 语音情绪
- 文本情绪
- 表情情绪
- 姿态情绪

### 5.3 量表侧如何绑定到 multimodal

量表每一题也定义为一个 turn，建议映射如下：

- `flow_run_id = assessment_session.id`
- `question_key = {scale_slug}-{序号3位}`
- `stage_id = scale_slug`
- `node_id = question_key`
- `turn_id = assessment_turn_id`

示例：

- `flow_run_id = 量表会话 session_id`
- `question_key = phq9-003`
- `stage_id = phq9`
- `node_id = phq9-003`
- `turn_id = 当前题回答窗口 UUID`

这样 `multimodal-service` 不需要知道“这是咨询题还是量表题”，它只处理一个通用 turn。

## 6. 后端设计

## 6.1 assessment-service 的职责

这里要明确一个命名口径：

- `assessment-service` 是服务名
- 在当前系统语义里，它负责“量表问诊阶段”
- 它不是“最终临床评估结论服务”

也就是说：

- `assessment-service` 负责量表会话、逐题作答、单量表计分、全量表聚合
- `risk-service` 才负责“临床决策”阶段的规则执行、风险分层和最终风险结论输出

所以本文里提到 `assessment-service` 时，统一理解为：

- 服务名仍叫 `assessment-service`
- 中文职责表述统一写成“量表问诊服务”

量表问诊服务需要承担三件事：

1. 校验当前题是否允许提交
2. 把点击答案或语音文本归一化成一个标准选项
3. 保存量表题答案并推进 session

## 6.2 现有 `/answers` 接口需要扩展

当前 `POST /api/v1/assessment/sessions/{session_id}/answers` 只够支撑点击选项，不够支撑完整语音链路。

建议继续保留同一路径，但扩展 payload：

```ts
type SubmitAssessmentAnswerPayload = {
  item_id?: string | null;
  selected_option_score?: number | null;
  selected_option_label?: string | null;
  raw_input?: string | null;
  transcript_text?: string | null;
  transcript_source?: "dolphin_final" | "manual_click" | "rule_inferred" | null;
  audio_uri?: string | null;
  original_audio_uri?: string | null;
  normalized_wav_uri?: string | null;
  turn_id?: string | null;
  question_key?: string | null;
  response_started_at?: string | null;
  response_completed_at?: string | null;
  capture_timestamp?: string | null;
  answer_source?: "click" | "voice" | null;
};
```

返回体建议补充：

```ts
{
  assessment_session: ...,
  accepted_answer: {
    item_id: "...",
    selected_option_label: "...",
    selected_option_score: 2,
    answer_source: "voice",
    transcript_text: "最近几天吧",
    turn_id: "..."
  }
}
```

这里再明确一次：

- 提交给量表答案接口的“最终答案”必须是标准选项
- `transcript_text` 只是语音答题的原始转写证据，需要入库
- 不能把未经归一化的自由文本直接当成量表最终答案

## 6.3 自动选项判定

语音答题的核心不是 ASR，而是“把自然语言转成量表选项”。

建议采用两层判定：

### 第一层：规则归一化

直接命中以下信息：

- 选项原文
- 数字
- 排名表达
- 时间表达

例如 `PHQ-9`：

- “完全没有” -> 0
- “几天” -> 1
- “一半以上” -> 2
- “几乎每天” -> 3
- “选第二个” -> 1
- “B” -> 1

例如 `SDS`：

- “很少” -> 1
- “小部分时间” -> 2
- “相当多时间” -> 3
- “大部分时间” / “绝大部分” -> 4

### 第二层：轻量语义判定

当规则层不能直接命中时，执行后端语义归一化。

推荐顺序：

1. 规则关键词提取
2. 同义词词典映射
3. 仍无法判定时，进入轻量语义分析器

这里的“语义分析”先不建议引入重 LLM 主链，第一版可以是：

- 若文本包含“偶尔、几次、不是很多” -> 靠近低频选项
- 若文本包含“经常、很多天、老是” -> 靠近高频选项
- 若文本包含“每天、几乎天天、一直都是” -> 最高频选项

如果最终仍不能判定：

- 返回 `422`
- 前端右上角弹窗提示“未能识别出对应选项，请改用点击选择或更明确地回答”
- 弹窗 5s 后自动隐去
- 当前题不推进
- 当前题仍保持可点击选项、可重新录音

第一版不做“低置信度自动写入”，避免误判污染量表结果。

## 6.4 量表答案落库扩展

当前 `assessment_answers` 不足以承接完整语音链路。

建议直接扩展 `assessment_answers`，不额外新建表，先走最小可用方案。

新增字段建议：

- `question_key`
- `turn_id`
- `answer_source`
- `selected_option_label`
- `selected_option_score`
- `transcript_text`
- `transcript_source`
- `audio_uri`
- `original_audio_uri`
- `normalized_wav_uri`
- `response_started_at`
- `response_completed_at`
- `multimodal_session_id`

说明：

- `raw_input` 保留原始输入，可继续存点击选项原文或语音原始转写
- `normalized_option` 可以继续保留，但建议与 `selected_option_label` 统一
- `score_value` 可继续保留作为最终标准分值

如果后续发现量表题也需要完整 subtitle history、system prompt 回放，再单独加 `assessment_turns` 表；本次先不强制。

## 6.5 多模态数据如何“入库”

本次不要求量表问诊服务自己存全部多模态明细。

推荐做法：

- 原始音频、ASR、语音/文本/表情/姿态等明细继续由 `multimodal-service` 存
- `assessment_answers` 保存它们的关键引用字段
- 通过 `turn_id` 和 `multimodal_session_id` 实现量表答案与多模态结果绑定

这样可以复用现有模型和推理链，避免复制一套多模态存储逻辑。

## 7. 前端设计

## 7.1 当前量表页新增状态

量表页需要新增这些状态：

- `videoFinished`
- `isRecording`
- `isSubmittingVoiceAnswer`
- `playbackBlocked`
- `currentTurnId`
- `subtitleUserTranscript`
- `pendingAutoSelectedOption`
- `lastAcceptedAnswer`

## 7.2 左侧量表看板行为

规则如下：

- 视频没播完：所有选项禁用
- 视频播完后：允许点击
- 点击后：
  - 立即进入提交态
  - 本题选项高亮
  - 提交成功后推进下一题

语音回答成功后：

- 根据后端返回的归一化选项高亮当前选项
- 显示 800ms 的确认态
- 再推进下一题

## 7.3 底部控制条行为

量表页底部控制条建议改为：

- 按钮 1：开始录音 / 结束录音
- 按钮 2：重播当前题目
- 按钮 3：结束量表预览或退出

录音按钮启用条件：

- 当前题视频已播完
- 不在提交中
- 当前题未完成

## 7.4 字幕区行为

字幕区仿照数字人问诊页：

- 默认显示数字人当前题干
- 录音完成、Dolphin 返回最终文本后，追加显示：
  - `用户：{最终转写文本}`

若语义归一化失败：

- 保留用户转写文本
- 再追加系统提示：
  - `系统：未能识别出明确选项，请点击左侧选项或重新语音回答`
- 同时触发右上角 toast：
  - `未能识别出对应选项，请改用点击选择或更明确地回答`
- toast 5s 后自动消失

## 7.5 推进逻辑

当前题提交成功后：

1. 前端拿到新的 `assessment_session`
2. 解析新的 `current_scale_slug + current_item`
3. 映射到 `scale-assessment-v1` 对应视频
4. 重置：
   - `videoFinished = false`
   - `subtitleUserTranscript = null`
   - `pendingAutoSelectedOption = null`
5. 自动播放下一题视频

## 8. 前后端接口建议

## 8.1 保持现有答案提交路径

推荐不新增 `/voice-answer` 路径，而是统一复用：

- `POST /api/v1/assessment/sessions/{session_id}/answers`

原因：

- 点击和语音本质上都是“提交当前题答案”
- 只是输入来源不同
- 后端只需根据 `answer_source` 判断归一化策略

## 8.2 可新增的辅助接口

如果后续需要更清晰的播放器驱动，可新增：

- `GET /api/v1/assessment/sessions/{session_id}/current-question`

返回：

- 当前量表
- 当前题目
- 当前题视频元数据
- 当前题是否允许回答

但第一版不是必须，现有 `GET /sessions/{id}` 已基本够用。

## 9. 数据流

### 9.1 点击答题

1. 前端点击左侧选项
2. 调用 assessment answer submit
3. 量表问诊服务保存标准选项答案
4. 返回新 session
5. 前端推进下一题

### 9.2 语音答题

1. 前端开始录音
2. 前端结束录音
3. 上传原始音频到 multimodal-service
4. Dolphin 返回最终转写
5. 前端字幕区显示转写文本
6. 前端调用 assessment answer submit，并把转写文本作为归一化输入证据一起传给后端
7. 量表问诊服务完成“转写文本 -> 标准选项文案/分值”的归一化
8. 量表问诊服务把标准选项答案写入量表答案表，同时保存转写文本、音频 URI 和关联字段
9. 返回 accepted answer + new session
10. 前端高亮对应选项
11. 前端显示 800ms 确认态
12. 前端推进下一题

## 10. 推荐实现顺序

1. 扩展 `assessment_answers` 表与 schema
2. 扩展 `SubmitAssessmentAnswerRequest`
3. 在 assessment-service 增加“语音文本 -> 选项”归一化逻辑
4. 前端量表页接入数字人问诊页的录音/ASR链路
5. 语音回答成功后接入字幕显示
6. 语音回答成功后接入自动高亮选项
7. 提交成功后推进下一题
8. 刷新后恢复未完成量表进度

## 11. 验收标准

- 进入量表页后自动播放当前题视频
- 视频未播完时不能点击选项，也不能开始录音
- 视频播完后可以点击选项，也可以开始录音
- 点击选项后答案真实入库，并推进到下一题
- 语音回答后能得到 Dolphin 最终转写文本
- 字幕区能显示用户最终转写文本
- 后端能把转写文本归一化为标准选项
- 前端能自动高亮被判定的选项
- 原始音频 URI、转写文本、题目 key、选项分值、回答时间窗能按当前题绑定
- 多模态结果继续按当前 turn 更新，不破坏现有数字人问诊链路
- 刷新页面后可以恢复到正确量表和正确题目

## 12. 当前建议结论

这次实现最稳的路线不是“为量表语音答题另写一套新系统”，而是：

- 前端复用数字人问诊的录音、ASR、字幕、多模态刷新逻辑
- 后端复用 assessment-service 的答案提交主路径
- 中间只补一个“转写文本 -> 标准量表选项”的归一化层
- 数据侧只扩 `assessment_answers` 的必要字段，先不新建复杂 turn 表

这样改动最小，可追踪性最好，也最容易和现在已经跑通的数字人问诊链路保持一致。

## 13. 结果页与最终评估口径

这里再单独澄清一次，避免后面职责混淆：

- `assessment-service`
  - 负责量表问诊
  - 产出单量表结果和 `assessment_aggregate_payload`
- `risk-service`
  - 负责临床决策
  - 消费问诊结果、量表聚合结果、多模态特征
  - 输出 `risk_level`、风险解释、转诊建议等最终结论

所以：

- 如果当前结果页只是展示量表得分与量表聚合，可以直接读 `assessment-service`
- 如果结果页要展示“最终风险等级/最终评估结论/临床建议”，最终应来自 `risk-service` 的临床决策输出
