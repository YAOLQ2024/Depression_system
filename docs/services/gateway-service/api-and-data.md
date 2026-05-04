# `gateway-service` 服务接口与数据

## 1. 当前接口清单

| 接口 | 方法 | 用途 | 当前实现 |
| --- | --- | --- | --- |
| `/health/live` | `GET` | 存活检查 | 已实现 |
| `/health/ready` | `GET` | 就绪检查 | 已实现 |
| `/api/v1/auth/register` | `POST` | 代理注册 | 已实现 |
| `/api/v1/auth/login` | `POST` | 代理登录并写 cookie | 已实现 |
| `/api/v1/auth/logout` | `POST` | 删除 cookie 并通知 identity | 已实现 |
| `/api/v1/users/me` | `GET` | 通过 cookie 查当前用户 | 已实现 |
| `/api/v1/users/me/profile` | `PUT` | 通过 cookie 更新问诊准备字段 | 已实现 |
| `/api/v1/consultations` | `POST` | 创建问诊会话 | 已实现 |
| `/api/v1/consultations/{id}` | `GET` | 获取问诊状态 | 已实现 |
| `/api/v1/consultations/{id}/start` | `POST` | 启动正式问诊 | 已实现 |
| `/api/v1/consultations/{id}/turns` | `POST` | 提交问答轮次 | 已实现 |
| `/api/v1/catalog/doctor-personas` | `GET` | 读取数字医生配置目录 | 已实现 |
| `/api/v1/catalog/workflow-summary` | `GET` | 读取 workflow 摘要 | 已实现 |
| `/api/v1/system/bootstrap` | `GET` | 聚合前端启动所需摘要 | 已实现 |

## 2. 规划中的接口

| 接口 | 方法 | 用途 | 目标下游 |
| --- | --- | --- | --- |
| `/api/v1/assessment/sessions` | `POST` | 创建量表会话 | `assessment-service` |
| `/api/v1/assessment/sessions/{id}/answers` | `POST` | 提交量表答案 | `assessment-service` |

## 3. 配置与资源

环境变量/配置重点：

- `identity_service_url`
- `session_cookie_name`
- `cors_origins`
- `workflow_resources_dir`

运行时资源：

- `packages/workflow-resources/workflows/consultation-v1.yaml`
- `packages/workflow-resources/doctor-personas/*.yaml`

## 4. 返回结构

成功结构沿用当前约定：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

错误结构应继续保持可被前端统一消费：

```json
{
  "code": 4010,
  "message": "missing session cookie",
  "data": {}
}
```

## 5. 安全与权限

- 浏览器只与 `gateway-service` 通信
- gateway 通过 `mcs_session` cookie 识别登录态
- gateway 向 `identity-service` 转发时使用 `Authorization: Bearer <session_token>`
- 对 `consultation-service` 已采用统一的内部用户头透传方式
- 后续对 `assessment-service` 也应沿用同样的内部鉴权传递方式
