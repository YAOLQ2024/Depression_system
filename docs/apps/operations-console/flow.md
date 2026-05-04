# `operations-console` 应用流程设计

## 1. 当前主流程

1. 用户打开后台
2. 进入后台登录页
3. 登录成功后请求 `/users/me`
4. 再请求 `/system/bootstrap`
5. 如果角色不是 `admin` 或 `researcher`，进入无权限页
6. 否则进入后台概览页

## 2. 后续目标流程

1. 登录成功后进入概览页
2. 通过左侧导航进入用户、流程资源、量表、风险、干预、记录等模块
3. 查看详情、执行筛选、发起受控修改或导出
4. 对重要改动进行校验、确认和审计记录
5. 修改发布后回到资源详情页查看结果

## 3. 页面状态流转

认证态：

- `unauthenticated`
- `authenticating`
- `authenticated`
- `unauthorized`

后台资源态：

- `dashboard_loading`
- `dashboard_ready`
- `resource_list_loading`
- `resource_detail_ready`
- `resource_editing`
- `resource_publish_pending`
- `resource_publish_done`

## 4. 异常分支

未登录：

- 接口 401 时回退到登录页

无后台权限：

- 显示无权限页
- 不展示后台主体导航

后台聚合加载失败：

- 显示错误提示
- 允许重新加载

配置校验失败：

- 保留表单输入
- 展示字段级错误和资源级错误

导出失败：

- 保留导出参数
- 提供失败原因和重新发起入口

## 5. 对正式实现的约束

- 后台不能直接编辑文件系统上的 YAML 文件
- 后台所有配置改动都应经过服务端校验
- 后台对资源的读取与写入应具备审计和回滚意识
