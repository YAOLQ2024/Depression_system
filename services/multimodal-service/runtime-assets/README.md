# Runtime Assets Layout

This directory stores runtime assets that `multimodal-service` needs at runtime.

Current layout:

- `models/`
  - Non-EEG four-modality assets live here during development.
  - The service reads:
    - `models/text_emotion/`
    - `models/audio_emotion/`
    - `models/face_emotion/`
    - `models/pose_emotion/`
  - Includes the lightweight runtime scripts plus the large `.onnx` weights.
  - These large weights are tracked with Git LFS.
- `models/README.md`
  - Naming, scope, and ownership notes for the four non-EEG modalities.

- `asr/base.cn/`
  - Zhu Rui's Dolphin ASR runtime assets live here.
  - Required files: `base.cn.pt`, `train.yaml`, `units.txt`, `global_cmvn`
  - Team setup command: `python services/multimodal-service/scripts/fetch_dolphin_model.py`
  - Large binary weights should follow the same policy as the four emotion models:
    host mount during development, Git LFS for large weight files, and no baking
    into the image during local rebuilds.
- `tmp/`
  - Temporary upload normalization and ASR working files
  - Safe to delete when the service is stopped

Notes:

- Docker mounts this repository path into `multimodal-service`, so the runtime
  directory must stay fixed.
- Non-EEG emotion model assets now use `runtime-assets/models/` as the single
  source of truth.
- ASR assets should use the same governance strategy:
  `runtime-assets/asr/` as the single source of truth, mounted into the
  container at runtime, with only large binary weights tracked via Git LFS.
- Development builds should avoid baking these large `.onnx` files into the
  image. Compose mounts them from the host instead.
- Lightweight configs such as `train.yaml`, `units.txt`, and `global_cmvn`
  can stay in normal Git unless their size becomes abnormal.
