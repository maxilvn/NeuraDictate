"""Entry point - handles subprocess modes and launches main app."""

import os
import sys
import subprocess
import io

# ──────────────────────────────────────────────────────────────────────
# Subprocess mode handling (for PyInstaller bundles and dev mode alike)
# Must be at the top before any heavy imports.
# ──────────────────────────────────────────────────────────────────────
_MODE = os.environ.get("NEURADICTATE_MODE", "")


def _prepend_bundle_path():
    """Add PyInstaller bundle path to sys.path if frozen."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir and bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
    # Also add the directory containing this file (dev mode)
    here = os.path.dirname(os.path.abspath(__file__))
    if here and here not in sys.path:
        sys.path.insert(0, here)


if _MODE == "exec_script":
    # Run a Python script from a temp file (replaces `python -c script`)
    _prepend_bundle_path()
    _script_path = os.environ.get("NEURADICTATE_SCRIPT", "")
    if _script_path and os.path.exists(_script_path):
        try:
            with open(_script_path, "r", encoding="utf-8") as _f:
                _code = _f.read()
        finally:
            try:
                os.unlink(_script_path)
            except OSError:
                pass
        exec(compile(_code, "<settings_window>", "exec"), {"__name__": "__main__"})
    sys.exit(0)

if _MODE == "download_model":
    _prepend_bundle_path()
    from voice_input.transcriber import download_model
    download_model(os.environ.get("NEURADICTATE_MODEL", "small"))
    sys.exit(0)

if _MODE == "delete_model":
    _prepend_bundle_path()
    from voice_input.transcriber import delete_model
    delete_model(os.environ.get("NEURADICTATE_MODEL", ""))
    sys.exit(0)


# ──────────────────────────────────────────────────────────────────────
# Main mode — dependency check + run the app
# ──────────────────────────────────────────────────────────────────────

COMMON = [
    ("faster_whisper", "faster-whisper"),
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
]

MAC_ONLY = [
    ("rumps", "rumps"),
    ("Quartz", "pyobjc-framework-Quartz"),
    ("AppKit", "pyobjc-framework-Cocoa"),
]

WIN_ONLY = [
    ("pynput", "pynput"),
    ("pystray", "pystray"),
    ("PIL", "Pillow"),
    ("pyperclip", "pyperclip"),
    ("pyautogui", "pyautogui"),
]


def ensure_deps():
    # Skip entirely in PyInstaller bundle — everything is pre-bundled
    if getattr(sys, "frozen", False):
        return

    deps = COMMON[:]
    if sys.platform == "darwin":
        deps += MAC_ONLY
    else:
        deps += WIN_ONLY

    missing = []
    for mod, pip_name in deps:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pip_name)

    if missing:
        try:
            print(f"Installing: {', '.join(missing)}...")
        except Exception:
            pass
        attempts = [
            [sys.executable, "-m", "pip", "install", "--quiet", "--user"] + missing,
            [sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages"] + missing,
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
        ]
        last_err = None
        for cmd in attempts:
            try:
                subprocess.check_call(cmd)
                break
            except subprocess.CalledProcessError as e:
                last_err = e
        else:
            raise last_err


if __name__ == "__main__":
    _HEADLESS = os.environ.get("NEURADICTATE_HEADLESS") == "1"
    _FROZEN = getattr(sys, "frozen", False)

    # Skip headless re-exec when frozen (PyInstaller bundle already has no console)
    if not _FROZEN and not _HEADLESS and sys.platform == "darwin":
        if sys.stdout and sys.stdout.isatty():
            env = dict(os.environ, NEURADICTATE_HEADLESS="1")
            subprocess.Popen(
                [sys.executable, __file__],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
            subprocess.Popen(
                [
                    "osascript", "-e",
                    'try\n'
                    '  tell application "Terminal"\n'
                    '    if it is frontmost then close front window\n'
                    '  end tell\n'
                    'end try\n'
                    'try\n'
                    '  tell application "iTerm2"\n'
                    '    if it is frontmost then tell current session of current window to close\n'
                    '  end tell\n'
                    'end try',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            sys.exit(0)
    elif not _FROZEN and not _HEADLESS and sys.platform == "win32":
        _exe = os.path.basename(sys.executable).lower()
        if _exe == "python.exe" and sys.stdout and sys.stdout.isatty():
            _dir = os.path.dirname(sys.executable)
            _pythonw = os.path.join(_dir, "pythonw.exe")
            if not os.path.isfile(_pythonw):
                _pythonw = sys.executable
            env = dict(os.environ, NEURADICTATE_HEADLESS="1")
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                [_pythonw, __file__],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS,
                env=env,
            )
            sys.exit(0)

    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    try:
        ensure_deps()
        # In bundle: make sure bundle path is importable
        if _FROZEN:
            _prepend_bundle_path()
        from voice_input.app import main
        main()
    except Exception:
        err_path = os.path.join(
            os.path.expanduser("~/.cache/voice-input"), "ERROR.txt"
        )
        try:
            os.makedirs(os.path.dirname(err_path), exist_ok=True)
            with open(err_path, "w") as f:
                import traceback
                f.write(f"NeuraDictate failed to start:\n\n{traceback.format_exc()}\n")
                f.write(f"\nPython: {sys.executable}\nPlatform: {sys.platform}\n")
                f.write(f"Frozen: {_FROZEN}\n")
        except OSError:
            pass
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0, "NeuraDictate failed to start.\nSee ~/.cache/voice-input/ERROR.txt",
                    "NeuraDictate Error", 0x10,
                )
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                subprocess.Popen([
                    "osascript", "-e",
                    'display alert "NeuraDictate" message "Failed to start. See ~/.cache/voice-input/ERROR.txt"',
                ])
            except Exception:
                pass
