# `identity-service` 服务接口与数据

## 1. 当前接口清单

| 接口 | 方法 | 用途 | 当前实现 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已实现 |
| `/health/ready` | `GET` | 就绪检查 | 已实现 |
| `/api/v1/auth/register` | `POST` | 创建 participant 用户 | 已实现 |
| `/api/v1/auth/login` | `POST` | 校验账号并创建 session | 已实现 |
| `/api/v1/auth/logout` | `POST` | 删除 session | 已实现 |
| `/api/v1/roles` | `GET` | 返回角色列表 | 已实现 |
| `/api/v1/users/me` | `GET` | 返回当前用户 | 已实现 |
| `/api/v1/users/me/profile` | `PUT` | 更新问诊准备字段 | 已实现 |

## 2. 当前角色

- `admin`
- `researcher`
- `participant`

## 3. 当前数据模型

存储方式：

- PostgreSQL
- Alembic 管理表结构
- SQLAlchemy 模型负责运行期读写

### 3.1 users

核心字段：

- `id`
- `email`
- `password_hash`
- `password_salt`
- `full_name`
- `role`
- `profile_status`
- `gender`
- `age`
- `height_cm`
- `weight_kg`
- `marital_status`
- `parents_marital_status`
- `parents_occupation`
- `prior_psychiatric_visit`
- `created_at`
- `updated_at`

说明：

- `full_name` 仍是顶层用户字段
- 问诊准备相关字段后续统一按 `full_name`、`age`、`gender`、`height_cm`、`weight_kg`、`marital_status`、`parents_marital_status`、`parents_occupation`、`prior_psychiatric_visit` 收口
- `/api/v1/users/me/profile` 只基于当前 session token 解析出的用户执行更新，不接受客户端指定其他用户 id

### 3.2 sessions

核心字段：

- `token`
- `user_id`
- `created_at`
- `expires_at`

## 4. 当前返回要点

登录返回：

```json
{
  "code": 0,
  "message": "logged in",
  "data": {
    "session_token": "opaque-token",
    "user": {}
  }
}
```

注意：

- `session_token` 只应在服务间流转或由 gateway 写入 cookie
- 浏览器不应直接持有它作为长期业务状态

## 5. 鉴权规则

- `users/me` 与 `users/me/profile` 依赖 `Authorization: Bearer <session_token>`
- 缺 token 返回 4011
- token 失效或过期返回 4012

## 6. 后续数据演进方向

- 将问诊准备字段从用户表中适度拆分为独立 profile / intake 表
- 保持身份域和业务域边界清晰
- 不要把问诊记录、量表答案等继续堆进 `identity-service`
