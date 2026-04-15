"""Transcription via faster-whisper with auto device/quantization selection."""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime

from . import config

log = logging.getLogger(__name__)

_model_instance = None
_model_name = None
_model_lock = threading.Lock()
_gpu_available = None
_detected_language = None


def _has_gpu() -> bool:
    global _gpu_available
    if _gpu_available is not None:
        return _gpu_available
    try:
        import torch
        _gpu_available = torch.cuda.is_available()
    except ImportError:
        _gpu_available = False
    log.info("GPU acceleration: %s", "available" if _gpu_available else "not available")
    return _gpu_available


def _best_compute_type(use_gpu: bool) -> str:
    if use_gpu:
        return "float16"
    # Let CTranslate2 pick the fastest type for this CPU (ARM NEON, AVX, etc.)
    return "auto"


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
    compute_type = _best_compute_type(use_gpu)

    log.info("Loading model %s on %s (compute=%s)...", model_name, device, compute_type)

    if _is_model_downloaded(model_name):
        _write_download_status(model_name, "loading")
    else:
        _write_download_status(model_name, "downloading")

    t0 = time.monotonic()
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(config.MODEL_DIR),
    )
    log.info("Model %s loaded in %.1fs", model_name, time.monotonic() - t0)

    _write_download_status(model_name, "ready")
    return model


def get_model(cfg: dict):
    global _model_instance, _model_name

    model_name = cfg.get("model", "large-v3-turbo")
    if _model_instance is not None and _model_name == model_name:
        return _model_instance

    with _model_lock:
        # Re-check after acquiring lock
        if _model_instance is not None and _model_name == model_name:
            return _model_instance

        if _has_gpu():
            try:
                _model_instance = _load_model(model_name, use_gpu=True)
                _model_name = model_name
                return _model_instance
            except Exception as e:
                log.warning("GPU not available (%s), using CPU", e)

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

    global _detected_language

    language = cfg.get("language", "auto")
    kwargs = {}
    if language != "auto":
        kwargs["language"] = language
    elif _detected_language:
        kwargs["language"] = _detected_language

    t0 = time.monotonic()

    segments, info = model.transcribe(
        wav_path,
        beam_size=1,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
        **kwargs,
    )

    t1 = time.monotonic()

    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())

    text = " ".join(text_parts).strip()
    text = " ".join(text.split())

    t2 = time.monotonic()

    if language == "auto" and info.language_probability > 0.7:
        _detected_language = info.language

    log.info(
        "Transcribed (%s, audio=%.1fs): init=%.1fs decode=%.1fs total=%.1fs | %s",
        info.language, info.duration,
        t1 - t0, t2 - t1, t2 - t0,
        text[:80],
    )
    return text


def download_model(model_name: str) -> bool:
    """Download a model without loading it for transcription."""
    if _is_model_downloaded(model_name):
        return True
    try:
        _write_download_status(model_name, "downloading")
        log.info("Downloading model %s...", model_name)
        from faster_whisper import WhisperModel
        WhisperModel(model_name, device="cpu", compute_type="int8",
                     download_root=str(config.MODEL_DIR))
        _write_download_status(model_name, "ready")
        log.info("Model %s downloaded successfully", model_name)
        return True
    except Exception:
        log.exception("Failed to download model %s", model_name)
        return False


def delete_model(model_name: str) -> bool:
    """Delete a downloaded model from disk."""
    import shutil
    if not config.MODEL_DIR.exists():
        return False
    for entry in config.MODEL_DIR.iterdir():
        if entry.is_dir() and model_name in entry.name:
            shutil.rmtree(entry)
            log.info("Deleted model %s", model_name)
            return True
    return False


def unload_model():
    global _model_instance, _model_name
    with _model_lock:
        _model_instance = None
        _model_name = None
