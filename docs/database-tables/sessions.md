# `sessions` 表说明

## 1. 表作用

`sessions` 用来保存登录后的会话令牌，是当前身份鉴权链路里的临时凭据表。

它不保存用户资料本身，只负责回答两个问题：

- 这个 token 属于谁？
- 这个 token 现在是否还有效？

## 2. 在系统哪一步使用

1. 登录流程：账号密码校验通过后，创建一条 session 记录。
2. 当前用户查询流程：读取 `Authorization` 头里的 token，再用本表校验有效性。
3. 问诊准备更新流程：先依赖本表完成鉴权，再允许更新 `users`。
4. 登出流程：删除对应 token 记录。
5. 过期清理流程：如果服务发现 token 已过期，会删除这条 session。

## 3. 字段说明

| 字段名 | 英文翻译 | 中文翻译 | 类型/约束 | 作用 | 为什么需要这个字段 | 主要使用步骤 |
| --- | --- | --- | --- | --- | --- | --- |
| `token` | Session Token | 会话令牌 | `String(255)`，主键 | 作为登录后的唯一凭据，客户端或 gateway 通过它代表当前用户。 | 如果没有独立 token，服务只能反复传密码，既不安全也不符合会话鉴权模式。 | 登录、鉴权、登出 |
| `user_id` | User ID | 用户ID | `String(36)`，外键到 `users.id`，非空 | 指向这条 session 属于哪位用户。 | token 本身只是随机串，必须依赖 `user_id` 才能映射回真实用户。 | 登录写入、当前用户查询 |
| `created_at` | Created Time | 创建时间 | `DateTime(timezone=True)`，非空 | 记录 session 生成时间。 | 需要知道 token 的签发时间，用于审计和排查异常登录。 | 登录、审计 |
| `expires_at` | Expiration Time | 过期时间 | `DateTime(timezone=True)`，非空 | 定义 token 的失效时刻。 | 没有过期时间会导致 token 长期有效，安全风险过高。 | 鉴权、过期清理 |

## 4. 备注

- 这张表采用 `token` 作为主键，说明系统当前使用的是“服务端保存会话”的模式，而不是完全无状态的 JWT 模式。
- `ondelete="CASCADE"` 说明删除用户时，其 session 会一起删除，避免无主 token 残留。
