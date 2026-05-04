# 服务文档目录说明

`docs/services/` 用来放后端服务级设计文档，目录结构应与 `services/` 对齐。

当前约定：

- 每个服务使用独立目录：`docs/services/<service-name>/`
- 每个服务至少先有 4 份文档：
  - `overview.md`
  - `api-and-data.md`
  - `flow.md`
  - `tasks.md`
- 接口设计、数据模型、状态流转先写文档，再动服务代码
- 如果服务边界变化，先改文档再改实现

写法要求参考了 `aic-coralreef` 的公共服务和业务应用文档，统一采用：

- 全文中文
- 先给设计结论，再展开架构、数据、接口、流程
- 用表格说明接口、数据模型、权限和依赖
- 把“负责什么、不负责什么、当前限制是什么”写清楚
- 文档能直接指导编码、联调和后续拆分

第一批优先写细的服务：

- `gateway-service`
- `identity-service`
- `consultation-service`
- `assessment-service`

其余服务先保留目录占位，等主链推进时再补细。
