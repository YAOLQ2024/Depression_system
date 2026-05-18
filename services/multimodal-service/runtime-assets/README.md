# Runtime Assets Layout

This directory stores runtime assets that `multimodal-service` needs at runtime.

Current layout:

- `asr/base.cn/`
  - Install the Dolphin `base.cn` model files here.
  - Required files: `base.cn.pt`, `train.yaml`, `units.txt`, `global_cmvn`
  - Team setup command: `python infra/scripts/fetch_dolphin_base_cn.py`
- `tmp/`
  - Temporary upload normalization and ASR working files
  - Safe to delete when the service is stopped

Notes:

- ASR model files are intentionally ignored by Git.
- Docker mounts this repository path into `multimodal-service`, so the install
  directory must stay fixed.
- Non-EEG emotion model assets live under `app/models/non_eeg/`, not in
  `runtime-assets/`.
