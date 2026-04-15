"""Configuration management - loads/saves settings as JSON."""

import json
import os
import sys
from pathlib import Path

APP_NAME = "NeuraDictate"

DEFAULT_CONFIG = {
    "hotkey": "Key.alt_r",
    "model": "large-v3-turbo",
    "language": "auto",
    "auto_paste": True,
    "gpu_enabled": True,
}

AVAILABLE_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3-turbo",
    "large-v3",
]

AVAILABLE_LANGUAGES = {
    "auto": "Auto-Detect",
    "de": "Deutsch",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português",
    "nl": "Nederlands",
    "pl": "Polski",
    "ja": "日本語",
    "zh": "中文",
    "ko": "한국어",
}

HOTKEY_OPTIONS = {
    "Key.alt_r": "Right Alt",
    "Key.caps_lock": "Caps Lock",
    "Key.scroll_lock": "Scroll Lock",
    "Key.pause": "Pause",
}


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    d = base / "voice-input"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".cache"
    d = base / "voice-input"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _model_dir() -> Path:
    d = _cache_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_PATH = _config_dir() / "config.json"
CACHE_DIR = _cache_dir()
MODEL_DIR = _model_dir()
RECORDING_PATH = CACHE_DIR / "current.wav"
LAST_TRANSCRIPT_PATH = CACHE_DIR / "last.txt"
TRANSCRIPT_HISTORY_PATH = CACHE_DIR / "history.json"
STATUS_PATH = CACHE_DIR / "status.json"
LOG_PATH = CACHE_DIR / "app.log"
PID_PATH = CACHE_DIR / "app.pid"


def load() -> dict:
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                stored = json.load(f)
            config.update(stored)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
