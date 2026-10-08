from pathlib import Path


def test_external_engine_keeps_original_onnx_for_fallback(monkeypatch):
    from app.services import non_eeg_runtime as runtime

    model = Path("/app/runtime-assets/models/pose_emotion/model.onnx")
    plan = Path("/app/board-engines/pose_emotion/model.plan")
    captured = {}
    sentinel = object()
    monkeypatch.setenv("MCS_TENSORRT_ENGINE_DIR", "/app/board-engines")
    monkeypatch.setattr(runtime, "_TENSORRT_ENABLED", True)
    monkeypatch.setattr(Path, "is_file", lambda path: path == plan)

    def build(path, *, onnx_path):
        captured.update(plan=path, onnx=onnx_path)
        return sentinel

    monkeypatch.setattr(runtime, "_TensorRTSession", build)
    assert runtime._inference_session(str(model)) is sentinel
    assert captured == {"plan": plan, "onnx": model}


def test_missing_external_engine_uses_onnx(monkeypatch):
    from app.services import non_eeg_runtime as runtime

    model = "/app/runtime-assets/models/audio_emotion/model.onnx"
    captured = {}
    sentinel = object()
    monkeypatch.setenv("MCS_TENSORRT_ENGINE_DIR", "/app/board-engines")
    monkeypatch.setattr(runtime, "_TENSORRT_ENABLED", True)
    monkeypatch.setattr(Path, "is_file", lambda path: False)

    def cpu(path, **kwargs):
        captured.update(path=path, options=kwargs)
        return sentinel

    monkeypatch.setattr(runtime, "_ORIGINAL_INFERENCE_SESSION", cpu)
    assert runtime._inference_session(model, providers=["CPUExecutionProvider"]) is sentinel
    assert captured == {"path": model, "options": {"providers": ["CPUExecutionProvider"]}}
