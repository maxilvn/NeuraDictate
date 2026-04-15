"""Auto-install dependencies if missing, then launch Voice Input."""

import subprocess
import sys
import os
import io

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
        # pythonw on Windows has no stdout, so guard prints
        try:
            print(f"Installing: {', '.join(missing)}...")
        except Exception:
            pass
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing
        )


if __name__ == "__main__":
    # --- Headless re-exec: detach from any visible terminal ---------------
    if sys.platform == "darwin":
        if sys.stdout and sys.stdout.isatty():
            devnull = open(os.devnull, "w")
            subprocess.Popen(
                [sys.executable, __file__],
                stdout=devnull,
                stderr=devnull,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            sys.exit(0)
    elif sys.platform == "win32":
        _exe = os.path.basename(sys.executable).lower()
        if _exe == "python.exe" and sys.stdout and sys.stdout.isatty():
            _dir = os.path.dirname(sys.executable)
            _pythonw = os.path.join(_dir, "pythonw.exe")
            if not os.path.isfile(_pythonw):
                _pythonw = sys.executable  # fallback
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                [_pythonw, __file__],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS,
            )
            sys.exit(0)

    # Ensure stdout/stderr exist (pythonw sets them to None)
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    ensure_deps()
    from voice_input.app import main
    main()
