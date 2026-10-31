## EEG Runtime Assets

This directory stores runtime EEG assets for `multimodal-service`.

Current model:

- Model file: `EEG_model.pkl`
- Version: `muser5s_m1_holdout_v1` (SVM, 156 aggregate inputs)
- Local adapter source: repository-root `model_runtime.py` from `three_52_new`
- Target usage: three-class EEG inference inside `depression-system`

Requirements:

- Runtime code must read assets from this repository only.
- Do not depend on an external absolute path under `three_52_new`.
- If the model artifact is replaced, update the deployment environment so the
  installed `scikit-learn` version remains compatible with the pickle file.

## M1 independent calibration (2026-10-25)

The server adapter lives in `app/services/eeg_model_runtime.py`. Loading M1
does not require a separate calibration file. On the first EEG turn of a new
multimodal session, the service collects 87 finite, unlabelled 52-feature
packets. These packets are used only for calibration, never for classification.
Packets received before an EEG turn is active are ignored for calibration.
Wave previews continue during calibration; no prediction or emotion avatar
classification is produced yet.

Calibration uses float64 means and sample standard deviations (`ddof=1`),
with standard deviations floored at `1e-8`. These statistics stay fixed for
subsequent classification. Each prediction uses exactly four new feature
frames, aggregated as median / population standard deviation / normalized-time
slope into 156 values, then passed through the bundle's scaler and SVM.
M1's four-frame requirement overrides the legacy ten-frame environment settings.
A partial window at turn end does not produce a prediction.

Calibration survives turn changes and gaps in the same session. Changing
session or restarting the service discards it and requires new calibration;
another participant's statistics are never used. This implementation uses
live collection. The adapter also retains the local `load_calibration()` helper
for an NPZ with an explicit `calibration` array, but no automatic shared-file
loading or calibration-upload API is configured.

Health, turn-start and live payloads expose a `calibration` object containing
`required`, `status` (`pending`, `collecting`, `ready`, or `not_required`),
`collected_frames` and `target_frames`. During collection `eeg_live.status` is
`calibrating`; the consultation display shows progress. Health readiness still
means model/transport readiness, so a service awaiting participant calibration
can accept sessions. `classification_ready` reports model/calibration readiness
separately and does not assert transport connectivity.

No model replacement or dependency change is needed. Deployment requires
rebuilding the multimodal-service image and the consultation frontend; the
existing runtime-assets mount and EEG bridge configuration can be retained.

Regression coverage: `tests/test_eeg_m1_runtime.py`, the existing EEG protocol /
runtime suites, and the model-input persistence test in `test_eeg_explanations.py`.
Synthetic input tests verify numerical agreement and session isolation; they do
not validate emotion accuracy or physical-device acquisition.

## Optional real SHAP reference assets (2026-10-22)

The legacy v20 SVM aggregates 156 features, then selects/scales 110 inputs. The independent CPU explanation worker currently supports that 110-input contract and expects a curated `background.npz` with `scaled_features` (N×110), plus a matching `background.json` manifest. M1 selects all 156 inputs; adapting SHAP and preparing a matching reference set are separate work. Its predictions are stored with their actual aggregate/scaled input snapshots, but the existing explanation endpoint returns `unsupported_model_input` for them. No simulated reference data are supplied in this runtime directory. Asset fields, deployment and acceptance scope: [EEG mirror implementation](../../../../docs/multiEmo/eeg-mirror-implementation_20261022.md).
