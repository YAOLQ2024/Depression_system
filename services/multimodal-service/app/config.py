from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _as_csv_list(value: str | None, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    items = [item.strip() for item in value.split(",")]
    normalized = [item for item in items if item]
    return normalized or list(default)


@lru_cache(maxsize=1)
def get_settings() -> dict:
    service_root = Path(__file__).resolve().parents[1]
    runtime_assets_dir = Path(
        os.getenv(
            "RUNTIME_ASSETS_DIR",
            str(service_root / "runtime-assets"),
        )
    )
    model_root = runtime_assets_dir / "models"
    eeg_root = runtime_assets_dir / "eeg"

    model_providers = _as_csv_list(
        os.getenv("MODEL_PROVIDERS") or os.getenv("MODEL_PROVIDER"),
        ["CPUExecutionProvider"],
    )
    eeg_channel_names = _as_csv_list(
        os.getenv("EEG_CHANNEL_NAMES"),
        ["T7", "T8", "Fpz"],
    )

    return {
        "app_name": os.getenv("APP_NAME", "Multimodal Service"),
        "database_url": os.getenv(
            "DATABASE_URL",
            "postgresql://mcs:mcs@127.0.0.1:5432/mcs",
        ),
        "redis_enabled": _as_bool(os.getenv("REDIS_ENABLED"), False),
        "redis_url": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0").strip(),
        "redis_key_prefix": os.getenv("REDIS_KEY_PREFIX", "mcs:multimodal").strip()
        or "mcs:multimodal",
        "redis_socket_timeout_seconds": _as_int(
            os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS"),
            2,
        ),
        "redis_connect_timeout_seconds": _as_int(
            os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS"),
            2,
        ),
        "redis_health_check_interval_seconds": _as_int(
            os.getenv("REDIS_HEALTH_CHECK_INTERVAL_SECONDS"),
            30,
        ),
        "visual_live_ttl_seconds": _as_int(
            os.getenv("VISUAL_LIVE_TTL_SECONDS"),
            300,
        ),
        "visual_turn_aggregate_ttl_seconds": _as_int(
            os.getenv("VISUAL_TURN_AGGREGATE_TTL_SECONDS"),
            1800,
        ),
        "visual_turn_frames_ttl_seconds": _as_int(
            os.getenv("VISUAL_TURN_FRAMES_TTL_SECONDS"),
            1800,
        ),
        "visual_turn_candidates_ttl_seconds": _as_int(
            os.getenv("VISUAL_TURN_CANDIDATES_TTL_SECONDS"),
            1800,
        ),
        "visual_turn_state_ttl_seconds": _as_int(
            os.getenv("VISUAL_TURN_STATE_TTL_SECONDS"),
            1800,
        ),
        "visual_turn_candidate_limit": _as_int(
            os.getenv("VISUAL_TURN_CANDIDATE_LIMIT"),
            16,
        ),
        "visual_turn_recent_frame_limit": _as_int(
            os.getenv("VISUAL_TURN_RECENT_FRAME_LIMIT"),
            64,
        ),
        "visual_turn_coarse_checkpoint_enabled": _as_bool(
            os.getenv("VISUAL_TURN_COARSE_CHECKPOINT_ENABLED"),
            True,
        ),
        "visual_turn_first_checkpoint_interval_seconds": _as_int(
            os.getenv("VISUAL_TURN_FIRST_CHECKPOINT_INTERVAL_SECONDS"),
            20,
        ),
        "visual_turn_first_checkpoint_min_frame_count": _as_int(
            os.getenv("VISUAL_TURN_FIRST_CHECKPOINT_MIN_FRAME_COUNT"),
            10,
        ),
        "visual_turn_subsequent_checkpoint_interval_seconds": _as_int(
            os.getenv("VISUAL_TURN_SUBSEQUENT_CHECKPOINT_INTERVAL_SECONDS"),
            30,
        ),
        "visual_turn_subsequent_checkpoint_min_frame_count": _as_int(
            os.getenv("VISUAL_TURN_SUBSEQUENT_CHECKPOINT_MIN_FRAME_COUNT"),
            20,
        ),
        "visual_turn_finalized_aggregate_ttl_seconds": _as_int(
            os.getenv("VISUAL_TURN_FINALIZED_AGGREGATE_TTL_SECONDS"),
            1800,
        ),
        "visual_turn_finalized_state_ttl_seconds": _as_int(
            os.getenv("VISUAL_TURN_FINALIZED_STATE_TTL_SECONDS"),
            1800,
        ),
        "visual_key_frame_strategy_version": os.getenv(
            "VISUAL_KEY_FRAME_STRATEGY_VERSION",
            "visual-key-frame-v1",
        ).strip()
        or "visual-key-frame-v1",
        "visual_key_frame_long_turn_step_seconds": _as_int(
            os.getenv("VISUAL_KEY_FRAME_LONG_TURN_STEP_SECONDS"),
            20,
        ),
        "visual_key_frame_default_max_count": _as_int(
            os.getenv("VISUAL_KEY_FRAME_DEFAULT_MAX_COUNT"),
            5,
        ),
        "visual_key_frame_hard_max_count": _as_int(
            os.getenv("VISUAL_KEY_FRAME_HARD_MAX_COUNT"),
            8,
        ),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        "minio_access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        "minio_secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        "minio_secure": _as_bool(os.getenv("MINIO_SECURE"), False),
        "multimodal_bucket": os.getenv("MULTIMODAL_BUCKET", "mcs-multimodal"),
        "runtime_assets_dir": runtime_assets_dir,
        "dolphin_model_name": os.getenv("DOLPHIN_MODEL_NAME", "base.cn.streaming"),
        "dolphin_model_repo_id": os.getenv("DOLPHIN_MODEL_REPO_ID", "").strip(),
        "dolphin_model_dir": Path(
            os.getenv(
                "DOLPHIN_MODEL_DIR",
                str(runtime_assets_dir / "asr" / "base.cn.streaming"),
            )
        ),
        "asr_device": os.getenv("ASR_DEVICE", "auto").strip().lower() or "auto",
        "asr_sync_timeout_ms": _as_int(
            os.getenv("ASR_SYNC_TIMEOUT_MS"),
            15000,
        ),
        "asr_preview_max_duration_ms": _as_int(
            os.getenv("ASR_PREVIEW_MAX_DURATION_MS"),
            10000,
        ),
        "asr_lang_sym": os.getenv("ASR_LANG_SYM", "zh"),
        "asr_region_sym": os.getenv("ASR_REGION_SYM", "CN"),
        "upload_max_bytes": 25 * 1024 * 1024,
        "upload_max_duration_ms": 60_000,
        "upload_processing_dir": runtime_assets_dir / "tmp",
        "model_providers": model_providers,
        "pose_window": int(os.getenv("POSE_WINDOW", "96")),
        "pose_state_idle_ttl_seconds": _as_int(
            os.getenv("POSE_STATE_IDLE_TTL_SECONDS"),
            120,
        ),
        "model_root": str(model_root),
        "text_model_dir": str(model_root / "text_emotion"),
        "audio_model_dir": str(model_root / "audio_emotion"),
        "face_model_dir": str(model_root / "face_emotion"),
        "pose_model_dir": str(model_root / "pose_emotion"),
        "eeg_enabled": _as_bool(os.getenv("EEG_ENABLED"), False),
        "eeg_provider": os.getenv("EEG_PROVIDER", "ble").strip().lower() or "ble",
        "eeg_device_name_hint": os.getenv("EEG_DEVICE_NAME_HINT", "EEG").strip() or "EEG",
        "eeg_notify_char_uuid": (
            os.getenv("EEG_NOTIFY_CHAR_UUID", "6e400003-b5a3-f393-e0a9-e50e24dcca9e").strip()
            or "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
        ),
        "eeg_scan_seconds": float(os.getenv("EEG_SCAN_SECONDS", "5")),
        "eeg_reconnect_delay_seconds": float(os.getenv("EEG_RECONNECT_DELAY_SECONDS", "5")),
        "eeg_sampling_rate": _as_int(os.getenv("EEG_SAMPLING_RATE"), 500),
        "eeg_preview_seconds": _as_int(os.getenv("EEG_PREVIEW_SECONDS"), 4),
        "eeg_window_seconds": _as_int(os.getenv("EEG_WINDOW_SECONDS"), 60),
        "eeg_min_feature_frames": _as_int(os.getenv("EEG_MIN_FEATURE_FRAMES"), 1),
        "eeg_channel_names": eeg_channel_names,
        "eeg_root": eeg_root,
        "eeg_model_path": Path(
            os.getenv(
                "EEG_MODEL_PATH",
                str(eeg_root / "model_combined_3class.pkl"),
            )
        ),
        "eeg_live_ttl_seconds": _as_int(os.getenv("EEG_LIVE_TTL_SECONDS"), 30),
        "eeg_turn_state_ttl_seconds": _as_int(os.getenv("EEG_TURN_STATE_TTL_SECONDS"), 600),
        "eeg_turn_window_ttl_seconds": _as_int(os.getenv("EEG_TURN_WINDOW_TTL_SECONDS"), 600),
        "eeg_latest_results_limit": _as_int(os.getenv("EEG_LATEST_RESULTS_LIMIT"), 3),
    }
