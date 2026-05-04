# `operations-console` 应用接口与数据

## 1. 页面与阶段映射

当前与近期页面规划：

| 页面/视图 | 作用 | 当前状态 |
| --- | --- | --- |
| 后台登录页 | 管理员/研究员登录 | 已实现占位版 |
| 概览页 | 查看 workflow 和数字医生目录摘要 | 已实现占位版 |
| 用户与权限页 | 管理用户、角色、账号状态 | 待实现 |
| 流程资源页 | 查看/校验 workflow、剧本、人设、量表、规则 | 待实现 |
| 记录检索页 | 检索问诊、量表、风险、干预记录 | 待实现 |
| 导出与再评估页 | 报告导出、再评估任务管理 | 待实现 |

## 2. 当前依赖接口

| 接口 | 方法 | 用途 | 提供方 |
| --- | --- | --- | --- |
| `/api/v1/auth/login` | `POST` | 后台登录 | `gateway-service` |
| `/api/v1/auth/logout` | `POST` | 后台退出 | `gateway-service` |
| `/api/v1/users/me` | `GET` | 获取当前操作者信息 | `gateway-service` |
| `/api/v1/system/bootstrap` | `GET` | 获取 workflow 与数字医生目录摘要 | `gateway-service` |

## 3. 规划中的新增接口

| 接口 | 方法 | 用途 | 目标服务 |
| --- | --- | --- | --- |
| `/api/v1/admin/users` | `GET` | 获取用户列表 | `gateway-service` 转发到 `identity-service` |
| `/api/v1/admin/users/{id}` | `PATCH` | 更新用户状态/角色 | `gateway-service` 转发到 `identity-service` |
| `/api/v1/admin/workflows/{id}` | `GET` | 获取 workflow 详情 | `gateway-service` 转发到资源管理接口 |
| `/api/v1/admin/interview-scripts/{bundle}` | `GET` | 获取剧本详情 | `gateway-service` 转发到 `consultation-service` |
| `/api/v1/admin/scales` | `GET` | 获取量表目录与状态 | `gateway-service` 转发到 `assessment-service` |
| `/api/v1/admin/risk-rules/{id}` | `GET` | 获取风险规则详情 | `gateway-service` 转发到 `risk-service` |
| `/api/v1/admin/intervention-programs` | `GET` | 获取干预方案目录 | `gateway-service` 转发到 `intervention-service` |
| `/api/v1/admin/reports/export` | `POST` | 生成导出任务 | `gateway-service` 转发到 `followup-service` |

## 4. 前端状态

当前占位版已有状态：

- `user`
- `bootstrap`
- `message`
- `error`

正式后台建议拆分为：

- `authStore`
- `dashboardStore`
- `userAdminStore`
- `workflowResourceStore`
- `recordsStore`
- `exportStore`

## 5. 关键数据结构

### 5.1 当前操作者

```json
{
  "id": "uuid",
  "email": "admin@mcs.local",
  "full_name": "系统管理员",
  "role": "admin"
}
```

### 5.2 后台启动摘要

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

### 5.3 规划中的资源摘要结构

```json
{
  "resource_type": "risk-rule",
  "resource_id": "consultation-v1",
  "status": "draft",
  "updated_at": "2026-04-30T12:00:00+08:00",
  "updated_by": "researcher@mcs.local"
}
```

## 6. 权限与校验

- 只有 `admin` 和 `researcher` 能进入后台
- 患者账号访问后台时应被明确拒绝
- 未来配置变更接口必须区分“只读查看”和“可发布修改”两级权限
- 导出接口应限制时间范围、记录范围和下载权限
