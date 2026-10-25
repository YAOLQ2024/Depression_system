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

## Optional real SHAP reference assets (2026-10-22)

The current default SVM aggregates 156 features, then selects/scales 110 inputs. The independent CPU explanation worker expects a curated `background.npz` with `scaled_features` (N×110), plus a matching `background.json` manifest. No simulated reference data are supplied in this runtime directory. Asset fields, deployment and acceptance scope: [EEG mirror implementation](../../../../docs/multiEmo/eeg-mirror-implementation_20261022.md).
