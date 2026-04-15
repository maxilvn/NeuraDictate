"""Clipboard copy and auto-paste."""

import subprocess
import sys
import threading
import time

_PASTE_LOCK = threading.Lock()
_LAST_PASTE_TEXT = None
_LAST_PASTE_AT = 0.0
_PASTE_DEDUP_WINDOW_SECONDS = 1.0


def _should_skip_duplicate_paste(text: str) -> bool:
    global _LAST_PASTE_TEXT, _LAST_PASTE_AT

    now = time.monotonic()
    if _LAST_PASTE_TEXT == text and (now - _LAST_PASTE_AT) < _PASTE_DEDUP_WINDOW_SECONDS:
        return True

    _LAST_PASTE_TEXT = text
    _LAST_PASTE_AT = now
    return False


def copy_and_paste(text: str, auto_paste: bool = True) -> None:
    """Copy text to clipboard and optionally simulate paste."""
    with _PASTE_LOCK:
        if sys.platform == "darwin":
            # Use pbcopy on Mac (reliable)
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))

            if auto_paste:
                if _should_skip_duplicate_paste(text):
                    return
                time.sleep(0.03)
                subprocess.run(
                    [
                        "osascript", "-e",
                        'tell application "System Events" to keystroke "v" using command down'
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        else:
            import pyperclip
            pyperclip.copy(text)

            if auto_paste:
                if _should_skip_duplicate_paste(text):
                    return
                import pyautogui
                time.sleep(0.06)
                pyautogui.hotkey("ctrl", "v")
