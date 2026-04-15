"""Transcription via faster-whisper with GPU→CPU fallback."""

import logging
import os

from . import config

log = logging.getLogger(__name__)

_model_instance = None
_model_name = None


def _load_model(model_name: str, use_gpu: bool):
    from faster_whisper import WhisperModel

    device = "cuda" if use_gpu else "cpu"
    compute_type = "float16" if use_gpu else "int8"

    log.info("Loading model %s on %s...", model_name, device)
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(config.MODEL_DIR),
    )


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
