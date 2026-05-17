# `assessment_results` 表说明

## 1. 表作用

`assessment_results` 用来保存“单份量表完成后”的计分结果。每完成一份量表，就会写入或更新一条结果记录。

它是量表域里的“结论层”数据，面向的是：

- 单量表得分结果展示
- 风险标记提取
- 多量表聚合与下游服务移交

## 2. 在系统哪一步使用

1. 单量表完成：从 `assessment_answers` 读取当前量表全部答案后计算得分并写入本表。
2. 全量表完成前汇总：收集所有结果记录生成 `aggregate_payload`。
3. 风险服务衔接：通过 `risk_flags`、解释等级和总分结果为后续风险判断提供结构化输入。

## 3. 字段说明

| 字段名 | 英文翻译 | 中文翻译 | 类型/约束 | 作用 | 为什么需要这个字段 | 主要使用步骤 |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | Assessment Result ID | 量表结果ID | `String(36)`，主键 | 唯一标识一条单量表结果。 | 每份量表都应有独立结果实体，便于引用和更新。 | 单量表完成、结果汇总 |
| `session_id` | Assessment Session ID | 量表会话ID | `String(36)`，外键到 `assessment_sessions.id`，索引，非空 | 表示该结果属于哪次量表会话。 | 一次评估会产生多份量表结果，必须归属于同一会话。 | 单量表完成、全量表聚合 |
| `scale_slug` | Scale Slug | 量表标识 | `String(128)`，非空 | 指明当前结果对应哪份量表。 | 不同量表的计分规则和解释规则不同，必须明确标识。 | 单量表完成、结果展示 |
| `raw_score` | Raw Score | 原始分 | `Integer`，非空 | 保存按量表规则直接计算得到的原始总分。 | 临床和研究经常需要原始分，不能只保留转换后的结果。 | 单量表完成、结果分析 |
| `derived_score` | Derived Score | 派生分/换算分 | `Integer`，非空 | 保存根据量表规则转换后的结果分。 | 有些量表需要标准分或换算分，单独落库可避免下游重复换算。 | 单量表完成、结果展示 |
| `interpretation_level` | Interpretation Level | 解释等级 | `String(128)`，可空 | 保存如轻度、中度、重度等等级代码。 | 代码化等级更适合程序判断和下游规则消费。 | 单量表完成、风险汇总 |
| `interpretation_label` | Interpretation Label | 解释标签 | `String(255)`，可空 | 保存面向展示的解释文本。 | 前端和报告层通常需要可直接显示的人类可读标签。 | 单量表完成、结果展示 |
| `risk_flags` | Risk Flags | 风险标记列表 | `JSON`，非空 | 保存由特定题目高分触发的风险标记。 | 仅有总分不足以覆盖关键风险题，必须保留更细粒度的风险信号。 | 单量表完成、风险服务衔接 |
| `completed_at` | Completed Time | 量表完成时间 | `DateTime(timezone=True)`，非空 | 记录该份量表得分生成的时间。 | 便于知道各量表的完成先后顺序，也利于时间线分析。 | 单量表完成、结果排序 |
| `created_at` | Created Time | 创建时间 | `DateTime(timezone=True)`，非空 | 记录结果首次创建时间。 | 需要区分“首次生成结果”和“后续更新结果”。 | 单量表完成、审计 |
| `updated_at` | Updated Time | 更新时间 | `DateTime(timezone=True)`，非空 | 记录结果最后一次更新时间。 | 若算法或答案修正导致重算，需要知道结果何时被更新。 | 结果重算、审计 |

## 4. 备注

- 表上存在唯一约束 `session_id + scale_slug`，确保同一场量表会话对同一份量表只有一条最终结果。
- `raw_score` 与 `derived_score` 分开保存，说明系统已经考虑到不同量表可能采用不同的换算逻辑，而不只是简单求和。
