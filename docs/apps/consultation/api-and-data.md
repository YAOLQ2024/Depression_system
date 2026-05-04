# `consultation` 应用接口与数据

## 1. 页面与阶段映射

当前与近期页面规划：

| 页面/视图 | 对应主流程阶段 | 当前状态 |
| --- | --- | --- |
| 登录/注册 | 患者登录 | 已实现占位版 |
| 问诊准备页 | 问诊准备 | 已实现占位版 |
| 正式问诊入口页 | 问诊准备 -> 数字人交互问诊 | 已实现占位版 |
| 数字人问诊页 | 数字人交互问诊 | 待实现 |
| 量表作答页 | 量表问诊 | 待实现 |
| 决策与干预页 | 临床决策 + 调节干预 | 待实现 |
| 回顾与再评估页 | 对话回顾与再评估 | 待实现 |

## 2. 当前依赖接口

| 接口 | 方法 | 用途 | 提供方 |
| --- | --- | --- | --- |
| `/api/v1/auth/register` | `POST` | 患者注册 | `gateway-service` |
| `/api/v1/auth/login` | `POST` | 患者登录 | `gateway-service` |
| `/api/v1/auth/logout` | `POST` | 退出登录 | `gateway-service` |
| `/api/v1/users/me` | `GET` | 拉取当前用户 | `gateway-service` |
| `/api/v1/users/me/profile` | `PUT` | 保存问诊准备字段 | `gateway-service` |
| `/api/v1/system/bootstrap` | `GET` | 拉取 workflow 与配置摘要 | `gateway-service` |
| `/api/v1/consultations` | `POST` | 创建问诊会话 | `gateway-service` |
| `/api/v1/consultations/{id}` | `GET` | 获取问诊状态 | `gateway-service` |
| `/api/v1/consultations/{id}/start` | `POST` | 启动正式问诊 | `gateway-service` |
| `/api/v1/consultations/{id}/turns` | `POST` | 提交患者问答轮次 | `gateway-service` |

## 3. 规划中的新增接口

| 接口 | 方法 | 用途 | 目标服务 |
| --- | --- | --- | --- |
| `/api/v1/assessment/sessions` | `POST` | 创建量表会话 | `gateway-service` 转发到 `assessment-service` |
| `/api/v1/assessment/sessions/{id}/answers` | `POST` | 提交量表答案 | `gateway-service` 转发到 `assessment-service` |

## 4. 前端状态

当前占位版已有状态：

- `user`
- `bootstrap`
- `message`
- `error`

正式 React 版建议拆分为：

- `authStore`
- `consultationPreparationStore`
- `consultationSessionStore`
- `assessmentSessionStore`
- `uiStore`

## 5. 关键数据结构

### 5.1 当前用户

```json
{
  "id": "uuid",
  "email": "participant@mcs.local",
  "full_name": "受试者示例账号",
  "role": "participant",
  "profile_status": "draft|completed",
  "profile": {
    "age": 25,
    "height_cm": 170,
    "weight_kg": 60,
    "marital_status": "未婚",
    "parents_marital_status": "已婚",
    "parents_occupation": "教师",
    "prior_psychiatric_visit": "无",
    "family_history": "无"
  }
}
```

### 5.2 Bootstrap 摘要

```json
{
  "workflow": {
    "workflow_id": "consultation-v1",
    "stage_count": 7,
    "stages": []
  },
  "doctor_personas": []
}
```

说明：

- `doctor_personas` 现在只作为系统配置目录摘要供后台与系统使用，不提供患者选择。

## 6. 表单与校验

问诊准备字段当前最少包括：

- `full_name`
- `age`
- `height_cm`
- `weight_kg`
- `marital_status`
- `parents_marital_status`
- `parents_occupation`
- `prior_psychiatric_visit`
- `family_history`

校验原则：

- `full_name` 必填
- 数值字段需要范围校验
- 文本字段允许留空，但正式版应补充长度限制和敏感词记录策略
