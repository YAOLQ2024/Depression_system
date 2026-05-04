# `assessment-service` 服务接口与数据

## 1. 建议接口清单

| 接口 | 方法 | 用途 | 规划状态 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已占位 |
| `/health/ready` | `GET` | 就绪检查 | 已占位 |
| `/api/v1/assessment/catalog` | `GET` | 返回当前活跃量表目录 | 规划中 |
| `/api/v1/assessment/sessions` | `POST` | 创建量表会话 | 规划中 |
| `/api/v1/assessment/sessions/{session_id}` | `GET` | 获取量表会话状态 | 规划中 |
| `/api/v1/assessment/sessions/{session_id}/answers` | `POST` | 提交单题答案 | 规划中 |
| `/api/v1/assessment/sessions/{session_id}/next` | `GET` | 获取下一题或下一量表 | 规划中 |
| `/api/v1/assessment/sessions/{session_id}/complete` | `POST` | 完成全部量表并生成聚合结果 | 规划中 |

## 2. 当前活跃量表

- `phq9`
- `sds`
- `sas`
- `social-function`

保留占位但不启用：

- `scl90`

## 3. 核心实体

### 3.1 assessment_session

- `session_id`
- `user_id`
- `consultation_session_id`
- `status`
- `required_scales`
- `selected_scales`
- `current_scale_slug`
- `current_item_index`
- `created_at`
- `updated_at`

### 3.2 assessment_answer

- `answer_id`
- `session_id`
- `scale_slug`
- `item_id`
- `raw_input`
- `normalized_option`
- `score_value`
- `created_at`

### 3.3 assessment_result

- `scale_slug`
- `raw_score`
- `derived_score`
- `interpretation`
- `completed_at`

## 4. 配置资源

必须读取：

- `scales/phq9.yaml`
- `scales/sds.yaml`
- `scales/sas.yaml`
- `scales/social-function.yaml`

可选保留：

- `scales/scl90.yaml`

## 5. 多模态数据关系

assessment-service 不直接完成多模态推理，但需要给 `multimodal-service` 预留关联字段：

- `session_id`
- `scale_slug`
- `item_id`
- `capture_timestamp`

## 6. 权限与调用

- 浏览器经 `gateway-service` 调用
- 会话必须绑定当前用户
- 单题答案提交需要防止跨会话写入
