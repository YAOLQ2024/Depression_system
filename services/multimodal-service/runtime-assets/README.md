# Runtime Assets Layout

This directory stores runtime assets that `multimodal-service` depends on.

Rules:

- Keep all runtime assets inside this repository.
- Do not reference assets from old local project paths.
- Do not rely on symlinks or absolute paths outside this service.

Current layout:

- `asr/base.cn/`
  - Install the Dolphin `base.cn` model files here.
  - The service validates that real model assets exist before accepting uploads.
- `tmp/`
  - Temporary upload normalization and ASR working files.
  - Safe to delete when the service is stopped.

Notes:

- Model files are intentionally ignored by Git.
- Docker copies and mounts assets only from this repository path.
- Team setup command:
  - `python infra/scripts/fetch_dolphin_base_cn.py`
