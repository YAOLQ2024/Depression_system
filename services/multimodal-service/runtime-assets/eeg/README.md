## EEG Runtime Assets

This directory stores runtime EEG assets for `multimodal-service`.

Current baseline:

- Model file: `EEG_model.pkl`
- Source baseline: `LAB_MDD/three_52_new`
- Target usage: three-class EEG inference inside `depression-system`

Requirements:

- Runtime code must read assets from this repository only.
- Do not depend on an external absolute path under `three_52_new`.
- If the model artifact is replaced, update the deployment environment so the
  installed `scikit-learn` version remains compatible with the pickle file.
