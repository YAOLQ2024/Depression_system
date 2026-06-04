## EEG Runtime Assets

This directory stores runtime EEG assets for `multimodal-service`.

Current baseline:

- Model file: `model_combined_3class.pkl`
- Source baseline: `LAB_MDD/three_52`
- Target usage: three-class EEG inference inside `depression-system`

Requirements:

- Runtime code must read assets from this repository only.
- Do not depend on an external absolute path under `three_52`.
- If the model artifact is replaced, update the deployment environment so the
  installed `scikit-learn` version remains compatible with the pickle file.
