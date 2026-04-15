"""Configuration management - loads/saves settings as JSON."""

import json
import os
import sys
from pathlib import Path

APP_NAME = "NeuraDictate"

DEFAULT_CONFIG = {
    "hotkey": "Key.alt_r",
    "model": "small",
    "language": "auto",
    "auto_paste": True,
    "gpu_enabled": True,
}

MODEL_INFO = {
    "tiny":            {"size": "75 MB",  "speed": 5, "quality": 2},
    "base":            {"size": "142 MB", "speed": 4, "quality": 3},
    "small":           {"size": "466 MB", "speed": 3, "quality": 4},
    "medium":          {"size": "1.5 GB", "speed": 2, "quality": 4},
    "large-v3-turbo":  {"size": "1.5 GB", "speed": 4, "quality": 5, "recommended": True},
    "large-v3":        {"size": "3 GB",   "speed": 1, "quality": 5},
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

MAC_HOTKEY_OPTIONS = {
    "fn": "Fn",
    "Key.alt_r": "Right Option",
    "Key.cmd_r": "Right Command",
    "Key.ctrl_l": "Left Control",
}

WIN_HOTKEY_OPTIONS = {
    "Key.alt_r": "Right Alt",
    "Key.caps_lock": "Caps Lock",
    "Key.scroll_lock": "Scroll Lock",
    "Key.pause": "Pause",
}

HOTKEY_OPTIONS = MAC_HOTKEY_OPTIONS if sys.platform == "darwin" else WIN_HOTKEY_OPTIONS


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
