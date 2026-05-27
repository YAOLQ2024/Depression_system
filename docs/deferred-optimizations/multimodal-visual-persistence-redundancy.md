# 视觉帧持久化结构冗余优化

## 问题描述

当前视觉关键帧持久化时，会同时写入：

- `multimodal_visual_frames`
- `multimodal_captures` 中的 `face` 记录
- `multimodal_captures` 中的 `pose` 记录
- `multimodal_inference_results` 中的 `face` 结果
- `multimodal_inference_results` 中的 `pose` 结果

这样 1 张关键帧会放大成 5 条记录。  
其中 `multimodal_visual_frames` 和视觉类 `multimodal_captures` 都重复保存了 `sample_index`、时间戳、`storage_uri` 等帧级信息，结构偏冗余。

## 解决方案

可选方案：

1. 保守方案：维持现状，只做字段约束和索引优化。
2. 简化方案：视觉链路只保留 `multimodal_visual_frames + multimodal_inference_results`，不再为每张视觉关键帧额外写 `face/pose capture`。

建议方向：

- 优先评估简化方案。
- 如果不影响现有查询和回放逻辑，再移除视觉类 `multimodal_captures`。
- 音频类 `multimodal_captures` 保留，不受这次优化影响。
