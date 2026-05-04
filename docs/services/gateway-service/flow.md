# `gateway-service` 服务流程设计

## 1. 当前认证流程

1. 浏览器向 `/api/v1/auth/login` 发送邮箱和密码
2. gateway 把请求转发给 `identity-service`
3. identity 返回 `session_token`
4. gateway 把 token 写入 `mcs_session` cookie
5. gateway 把脱敏后的用户信息返回给浏览器

## 2. 当前用户查询流程

1. 浏览器访问 `/api/v1/users/me`
2. gateway 从 cookie 里提取 `mcs_session`
3. gateway 以 `Authorization: Bearer <token>` 调 identity
4. identity 返回当前用户
5. gateway 透传给前端

## 3. Bootstrap 聚合流程

1. 浏览器访问 `/api/v1/system/bootstrap`
2. gateway 从本地 `workflow-resources` 读取 workflow 摘要
3. gateway 读取数字医生配置目录
4. gateway 聚合后返回给前端

## 4. 后续扩展流程

后续扩展时：

1. 前端仍先打 gateway
2. gateway 根据路由把请求分发到 `consultation-service` 或 `assessment-service`
3. 领域服务只处理业务，不直接面向浏览器

## 5. 异常分支

缺失 cookie：

- 返回 401

identity 不可用：

- 统一映射为 503

workflow 资源读取失败：

- 不应让前端拿到半截数据
- 应返回可识别的 5xx 错误并记录日志

## 6. 后续设计约束

- gateway 只做轻聚合与转发
- 一旦转发服务增多，应引入更清晰的 client 目录与错误码映射表
- bootstrap 的稳定性要高于普通业务接口，因为两个 app 都依赖它启动
