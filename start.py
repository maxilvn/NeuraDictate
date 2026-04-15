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
    _HEADLESS = os.environ.get("NEURADICTATE_HEADLESS") == "1"
    if not _HEADLESS and sys.platform == "darwin":
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
            # Close the Terminal window that launched us
            subprocess.Popen(["osascript", "-e",
                'tell application "Terminal" to close front window'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            sys.exit(0)
    elif not _HEADLESS and sys.platform == "win32":
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

    # Ensure stdout/stderr exist (pythonw sets them to None)
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    try:
        ensure_deps()
        from voice_input.app import main
        main()
    except Exception as e:
        # Write error to a visible file so user can diagnose
        err_path = os.path.join(os.path.dirname(__file__), "ERROR.txt")
        with open(err_path, "w") as f:
            import traceback
            f.write(f"NeuraDictate failed to start:\n\n{traceback.format_exc()}\n")
            f.write(f"\nPython: {sys.executable}\nPlatform: {sys.platform}\n")
        # Also try a system notification on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0, f"NeuraDictate failed to start.\nSee ERROR.txt for details.",
                    "NeuraDictate Error", 0x10)
            except Exception:
                pass
