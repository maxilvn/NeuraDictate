"""Transcription via faster-whisper with GPU→CPU fallback."""

import json
import logging
import os
from datetime import datetime

from . import config

log = logging.getLogger(__name__)

_model_instance = None
_model_name = None


def _write_download_status(model_name: str, state: str):
    """Write model loading status so control panel can show it."""
    try:
        status = {}
        if config.STATUS_PATH.exists():
            status = json.loads(config.STATUS_PATH.read_text(encoding="utf-8"))
        if state == "downloading":
            status["state"] = "downloading"
            status["detail"] = f"Downloading model: {model_name}..."
        elif state == "loading":
            status["state"] = "loading"
            status["detail"] = f"Loading model: {model_name}..."
        elif state == "ready":
            status["state"] = "hidden"
            status["detail"] = "Ready"
        status["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config.STATUS_PATH.write_text(
            json.dumps(status, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _is_model_downloaded(model_name: str) -> bool:
    """Check if model is already downloaded in MODEL_DIR."""
    if not config.MODEL_DIR.exists():
        return False
    for entry in config.MODEL_DIR.iterdir():
        if entry.is_dir() and model_name in entry.name:
            return True
    return False


def _load_model(model_name: str, use_gpu: bool):
    from faster_whisper import WhisperModel

    device = "cuda" if use_gpu else "cpu"
    compute_type = "float16" if use_gpu else "int8"

    log.info("Loading model %s on %s...", model_name, device)

    if _is_model_downloaded(model_name):
        _write_download_status(model_name, "loading")
    else:
        _write_download_status(model_name, "downloading")

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(config.MODEL_DIR),
    )

    _write_download_status(model_name, "ready")
    return model


def get_model(cfg: dict):
    global _model_instance, _model_name

    model_name = cfg.get("model", "large-v3-turbo")
    if _model_instance is not None and _model_name == model_name:
        return _model_instance

    use_gpu = cfg.get("gpu_enabled", True)

    if use_gpu:
        try:
            _model_instance = _load_model(model_name, use_gpu=True)
            _model_name = model_name
            return _model_instance
        except Exception as e:
            log.warning("GPU failed (%s), falling back to CPU", e)

    _model_instance = _load_model(model_name, use_gpu=False)
    _model_name = model_name
    return _model_instance


def warm_up_model(cfg: dict) -> None:
    """Preload the configured model in the background to reduce first-run latency."""
    try:
        get_model(cfg)
    except Exception:
        log.exception("Model warm-up failed")


def transcribe(wav_path: str, cfg: dict) -> str:
    """Transcribe a WAV file. Returns the transcribed text."""
    model = get_model(cfg)

    language = cfg.get("language", "auto")
    kwargs = {}
    if language != "auto":
        kwargs["language"] = language

    segments, info = model.transcribe(
        wav_path,
        beam_size=1,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
        **kwargs,
    )

    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())

    text = " ".join(text_parts).strip()
    # Normalize whitespace
    text = " ".join(text.split())

    log.info("Transcribed (%s, %.1fs): %s", info.language, info.duration, text[:80])
    return text


def unload_model():
    global _model_instance, _model_name
    _model_instance = None
    _model_name = None
