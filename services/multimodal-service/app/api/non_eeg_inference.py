from __future__ import annotations

from fastapi import APIRouter

from app.schemas import AudioEmotionInferRequest, FrameEmotionInferRequest, TextEmotionInferRequest
from app.services.non_eeg_inference import (
    infer_audio_emotion,
    infer_face_emotion,
    infer_pose_emotion,
    infer_text_emotion,
)

router = APIRouter(prefix="/api/v1/non-eeg")
legacy_router = APIRouter(prefix="/api/v1")


@router.post("/text-emotion/infer")
def text_emotion_infer(request: TextEmotionInferRequest) -> dict:
    return infer_text_emotion(request)


@router.post("/audio-emotion/infer")
def audio_emotion_infer(request: AudioEmotionInferRequest) -> dict:
    return infer_audio_emotion(request)


@router.post("/face-emotion/frame-infer")
def face_emotion_infer(request: FrameEmotionInferRequest) -> dict:
    return infer_face_emotion(request)


@router.post("/pose-emotion/frame-infer")
def pose_emotion_infer(request: FrameEmotionInferRequest) -> dict:
    return infer_pose_emotion(request)


# Backward-compatible aliases matching the original standalone 4-modality API.
@legacy_router.post("/text/infer", include_in_schema=False)
def text_emotion_infer_alias(request: TextEmotionInferRequest) -> dict:
    return infer_text_emotion(request)


@legacy_router.post("/audio/infer", include_in_schema=False)
def audio_emotion_infer_alias(request: AudioEmotionInferRequest) -> dict:
    return infer_audio_emotion(request)


@legacy_router.post("/emotion-recognition/frame-infer", include_in_schema=False)
def face_emotion_infer_alias(request: FrameEmotionInferRequest) -> dict:
    return infer_face_emotion(request)


@legacy_router.post("/pose/frame-infer", include_in_schema=False)
def pose_emotion_infer_alias(request: FrameEmotionInferRequest) -> dict:
    return infer_pose_emotion(request)
