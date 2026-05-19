# ASR Runtime Assets

这里是 `multimodal-service` 在开发环境下的 ASR 运行时资源目录。

当前约定：

- `asr/base.cn/` 作为 Dolphin `base.cn` 模型固定安装目录
- 目录路径与配置项 `DOLPHIN_MODEL_DIR=/app/runtime-assets/asr/base.cn` 保持一致
- 由 Compose 挂载整个 `runtime-assets/` 到容器内 `/app/runtime-assets`

团队协作规则：

- 大型权重文件统一走 Git LFS
  - 例如 `*.pt`、`*.bin`、`*.onnx`、`*.ckpt`、`*.safetensors`
- 轻量配置文件继续走普通 Git
  - 例如 `train.yaml`、`units.txt`、`global_cmvn`
- 开发环境不把大权重 bake 进镜像
  - 只通过宿主机挂载供容器读取

推荐安装方式：

- 执行：`python services/multimodal-service/scripts/fetch_dolphin_model.py`
- 安装完成后，模型文件应出现在：`runtime-assets/asr/base.cn/`
