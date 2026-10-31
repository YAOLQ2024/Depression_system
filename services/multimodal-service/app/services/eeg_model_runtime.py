"""Packet-to-model adapter migrated from the local model_runtime.py.

M1 statistics are fitted on independent calibration frames and remain fixed
while classifying subsequent windows. All calculations use float64, as in the
local adapter; the packet itself carries float32 values.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.services.eeg_protocol import MODEL_FEATURE_COUNT, MODEL_FEATURE_NAMES

MUSER_VERSION = "muser5s_m1_holdout_v1"


def normalize_bundle(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise ValueError("eeg_model_bundle_must_be_dict")
    normalized = dict(bundle)
    if normalized.get("version") == MUSER_VERSION:
        names = list(normalized.get("window_feature_names") or normalized.get("feature_names") or [])
        if len(names) != MODEL_FEATURE_COUNT:
            raise ValueError("eeg_m1_window_feature_count_mismatch")
        trial = [f"{part}_{name}" for part in ("med", "std", "slope") for name in names]
        normalized.update(
            classifier_name="SVM_Muser64_5s_M1",
            input_kind="vector",
            norm_mode="independent_calibration",
            runtime_feature_source="packet",
            packet_feature_names=names,
            window_feature_names=names,
            trial_feature_names=trial,
            all_feature_names=trial,
            feature_names=trial,
            selected_features=list(range(len(trial))),
            trial_feature_components=["med", "std", "slope"],
            runtime_window_frames=4,
            runtime_calibration_frames=87,
            feature_set_desc="T7/T8/Fpz 52维，独立M1校准，4帧聚合156维",
        )
    return normalized


class ModelRuntime:
    def __init__(self, bundle: dict[str, Any]) -> None:
        self.bundle = normalize_bundle(bundle)
        self.requires_calibration = self.bundle.get("norm_mode") == "independent_calibration"
        self.window_names = list(
            self.bundle.get("window_feature_names")
            or self.bundle.get("packet_feature_names")
            or MODEL_FEATURE_NAMES
        )
        if self.window_names != list(MODEL_FEATURE_NAMES):
            raise ValueError("eeg_packet_feature_order_mismatch")
        self.trial_names = list(
            self.bundle.get("trial_feature_names")
            or self.bundle.get("all_feature_names")
            or self.window_names
        )
        self.components = tuple(
            self.bundle.get("trial_feature_components")
            or (["med"] if len(self.trial_names) == len(self.window_names) else ["med", "std", "slope"])
        )
        self.selected = np.asarray(
            self.bundle.get("selected_features", np.arange(len(self.trial_names))), dtype=int
        )
        if len(self.trial_names) != len(self.window_names) * len(self.components):
            raise ValueError("eeg_trial_feature_count_mismatch")
        if any(component not in {"med", "std", "slope"} for component in self.components):
            raise ValueError("unsupported_eeg_trial_component")
        if (self.selected.ndim != 1 or not len(self.selected)
                or np.any(self.selected < 0) or np.any(self.selected >= len(self.trial_names))):
            raise ValueError("eeg_selected_feature_index_out_of_range")
        expected = len(self.selected)
        if (int(self.bundle["scaler"].n_features_in_) != expected
                or int(self.bundle["model"].n_features_in_) != expected):
            raise ValueError("eeg_model_feature_dimension_mismatch")
        self.required_frames = (
            int(self.bundle["runtime_window_frames"]) if self.requires_calibration else None
        )
        self.calibration_target = int(self.bundle.get("runtime_calibration_frames", 87))
        self.std_ddof = int(self.bundle.get("calibration_std_ddof", 1))
        self.std_floor = float(self.bundle.get("calibration_std_floor", 1e-8))
        if (self.calibration_target < 2 or not 0 <= self.std_ddof < self.calibration_target
                or not np.isfinite(self.std_floor) or self.std_floor <= 0
                or (self.required_frames is not None and self.required_frames < 1)):
            raise ValueError("invalid_eeg_calibration_configuration")
        self.reset_calibration()

    @property
    def calibrated(self) -> bool:
        return not self.requires_calibration or self.mean is not None

    def reset_calibration(self) -> None:
        self.calibration_rows: list[list[float]] = []
        self.mean: np.ndarray | None = None
        self.std: np.ndarray | None = None

    def set_calibration(self, rows: Any) -> None:
        values = np.asarray(rows, dtype=float)
        if (values.ndim != 2 or values.shape[1] != MODEL_FEATURE_COUNT
                or len(values) < max(2, self.std_ddof + 1) or not np.isfinite(values).all()):
            raise ValueError("invalid_eeg_calibration_rows")
        mean = values.mean(axis=0)
        std = np.maximum(values.std(axis=0, ddof=self.std_ddof), self.std_floor)
        if not np.isfinite(mean).all() or not np.isfinite(std).all():
            raise ValueError("nonfinite_eeg_calibration_statistics")
        self.mean, self.std = mean, std
        self.calibration_rows = values.copy().tolist()

    def load_calibration(self, path: str | Path) -> None:
        with np.load(Path(path), allow_pickle=False) as data:
            if "calibration" not in data:
                raise ValueError("eeg_calibration_array_missing")
            self.set_calibration(data["calibration"])

    def add_calibration(self, row: Any) -> bool:
        if self.calibrated:
            return True
        values = np.asarray(row, dtype=float)
        if values.shape != (MODEL_FEATURE_COUNT,) or not np.isfinite(values).all():
            raise ValueError("invalid_eeg_calibration_frame")
        self.calibration_rows.append(values.copy().tolist())
        if len(self.calibration_rows) >= self.calibration_target:
            self.set_calibration(self.calibration_rows)
        return self.calibrated

    def prepare(self, rows: Any) -> tuple[np.ndarray, np.ndarray]:
        values = np.asarray(rows, dtype=float)
        if (values.ndim != 2 or values.shape[1] != MODEL_FEATURE_COUNT
                or not len(values) or not np.isfinite(values).all()):
            raise ValueError("invalid_eeg_feature_rows")
        if self.required_frames and len(values) != self.required_frames:
            raise ValueError(f"eeg_window_frame_count_mismatch:expected={self.required_frames}")
        if not self.calibrated:
            raise ValueError("eeg_calibration_required")
        if self.requires_calibration:
            values = (values - self.mean) / self.std
        elif self.bundle.get("norm_mode", "none") == "session_zscore":
            std = values.std(axis=0)
            std[std < 1e-12] = 1
            values = (values - values.mean(axis=0)) / std
        time_axis = np.arange(len(values), dtype=float)
        time_axis -= time_axis.mean()
        slope = (
            np.zeros(MODEL_FEATURE_COUNT) if len(values) < 2
            else np.mean(values * (time_axis / time_axis.std())[:, None], axis=0)
        )
        parts = {"med": np.median(values, axis=0), "std": values.std(axis=0), "slope": slope}
        full = np.concatenate([parts[component] for component in self.components])
        scaled = self.bundle["scaler"].transform(full[self.selected].reshape(1, -1))
        return full, scaled
