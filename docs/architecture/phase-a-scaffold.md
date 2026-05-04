# Phase A Scaffold Status

Phase A 已完成以下内容：

1. 建立 `apps / services / packages / infra / docs` 骨架。
2. `apps/*` 采用 `aic-coralreef` 风格的 `client + server + Dockerfile + README + .gitignore + .gitattributes` 外壳。
3. `services/*` 采用统一 Python 服务模板：
   `app + alembic + Dockerfile + alembic.ini + pyproject.toml + requirements.txt + seed.py + scripts + tests`
4. 建立 `packages/workflow-resources/`，用于承载：
   - 产品流程
   - 规则版问诊脚本
   - 医生人设
   - 量表定义
   - 风险规则
   - 干预方案

已完成的资源初始化：

- `workflows/consultation-v1.yaml`
- `doctor-personas/*.yaml`
- `interview-scripts/rule-v1/*.yaml`
- `scales/*.yaml`
- `risk-rules/consultation-v1.yaml`
- `intervention-programs/catalog.yaml`

量表状态：

- `PHQ-9`：已结构化
- `SDS`：已结构化
- `SAS`：已结构化，计分细节需二次核对
- `社会功能缺陷量表（SDSS）`：已结构化
- `SCL-90`：已建立资源占位，但当前不纳入活跃 V1 主链；源文件为老 `.doc`，需后续人工核对/转录 90 个条目

Phase A 暂不做的事情：

- 不实现真实业务逻辑
- 不接旧系统运行时
- 不引入 LLM 主链
- 不对旧项目做代理兼容

下一阶段建议：

1. 在 `consultation-service` 中实现规则版状态机读取 `interview-scripts/`
2. 在 `assessment-service` 中实现量表定义读取与逐量表提交
3. 在 `gateway-service` 和 `identity-service` 中打通最小可运行链路
