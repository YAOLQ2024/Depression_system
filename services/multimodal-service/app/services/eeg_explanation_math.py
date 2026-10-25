"""Pure, versioned EEG input/attribution operations shared by API and worker."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

MAPPING_VERSION = "unique-channel-equal-split-v1"
PIPELINE_VERSION = "window-zscore-mss-v1"
OUTPUT_KIND = "svc_ovr_decision_score"
GROUPS = ("基础特征", "PAC", "AAC", "PPC")
CHANNELS = ("Fpz", "T7", "T8")


def digest_json(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def feature_mapping(names: list[str], selected: list[int]) -> list[dict]:
    result = []
    for i, index in enumerate(selected):
        name = names[index]
        statistic, _, base = name.partition("_")
        parts = base.split("_")
        channels = [c for c in CHANNELS if c in parts]
        if not channels or statistic not in {"med", "std", "slope"}:
            raise ValueError("unsupported_feature_mapping")
        result.append({"input_index": i, "aggregate_index": index, "name": name,
                       "statistic": statistic, "group": parts[0] if parts[0] in GROUPS else GROUPS[0],
                       "channel_weights": {c: 1 / len(channels) for c in channels}})
    return result


def freeze_input(*, model_sha256: str | None, feature_names: list[str],
                 selected: list[int], aggregated: np.ndarray, scaled: np.ndarray) -> dict:
    values = np.asarray(scaled).reshape(-1)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite_model_input")
    snapshot = {"model_sha256": model_sha256, "pipeline_version": PIPELINE_VERSION,
                "feature_names": [feature_names[i] for i in selected],
                "selected_indices": selected, "aggregate_vector": aggregated.tolist(),
                "scaled_vector": values.tolist()}
    snapshot["input_hash"] = digest_json(snapshot)
    return snapshot


def aggregate_contributions(phi: np.ndarray, mapping: list[dict], *,
                            base_value: float, target_output: float,
                            influence_floor: float = 1e-8) -> dict:
    values = np.asarray(phi, dtype=float).reshape(-1)
    if len(values) != len(mapping) or not np.isfinite(values).all():
        raise ValueError("invalid_attribution_shape")
    if not math.isfinite(base_value) or not math.isfinite(target_output):
        raise ValueError("nonfinite_model_output")
    groups = dict.fromkeys(GROUPS, 0.0)
    net = dict.fromkeys(CHANNELS, 0.0)
    absolute = dict.fromkeys(CHANNELS, 0.0)
    for value, item in zip(values, mapping):
        weights = item["channel_weights"]
        if abs(sum(weights.values()) - 1) > 1e-12 or any(w < 0 for w in weights.values()):
            raise ValueError("invalid_channel_weights")
        groups[item["group"]] += float(value)
        for channel, weight in weights.items():
            net[channel] += weight * float(value)
            absolute[channel] += weight * abs(float(value))
    total = sum(absolute.values())
    percentages = None
    if total > influence_floor:
        raw = [absolute[c] / total * 100 for c in CHANNELS]
        rounded = [math.floor(v) for v in raw]
        order = sorted(range(3), key=lambda i: raw[i] - rounded[i], reverse=True)
        for i in order[:100 - sum(rounded)]:
            rounded[i] += 1
        percentages = dict(zip(CHANNELS, rounded))
    error = abs(base_value + float(values.sum()) - target_output)
    if error > 1e-4 + 1e-3 * max(1, abs(target_output)):
        raise ValueError("additivity_check_failed")
    return {"phi": values.tolist(), "base_value": base_value, "target_output": target_output,
            "group_net": groups, "channel_net": net, "channel_abs": absolute,
            "channel_percent": percentages, "additivity_error": error}
