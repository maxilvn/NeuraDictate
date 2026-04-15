"""Main application - ties everything together."""

import json
import logging
import os
import sys
import threading
from datetime import datetime

from . import config
from .clipboard import copy_and_paste
from .hotkey import HotkeyListener
from .hud import HudOverlay, HudState
from .recorder import Recorder
from .settings_window import SettingsWindow
from .transcriber import transcribe, unload_model, warm_up_model
from .tray import TrayApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
    ],
    force=True,
)
log = logging.getLogger(__name__)


class VoiceInputApp:
    def __init__(self):
        self._cfg = config.load()
        self._recorder = Recorder()
        self._hud = HudOverlay()
        self._hotkey: HotkeyListener | None = None
        self._tray: TrayApp | None = None
        self._active = True
        self._transcribing = False

    def run(self) -> None:
        if not self._acquire_single_instance():
            log.info("Another instance is already running; opening control panel only")
            self._open_control_panel(blocking=True)
            return

        log.info("%s starting...", config.APP_NAME)
        self._write_status(HudState.HIDDEN, "Starting")

        # Start HUD overlay thread
        self._hud.start()

        # Start hotkey listener
        self._hotkey = HotkeyListener(
            hotkey_str=self._cfg.get("hotkey", "Key.alt_r"),
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._hotkey.start()
        self._write_status(HudState.HIDDEN, "Ready")

        # Preload the selected model so first transcription does not pay model-load cost.
        threading.Thread(target=warm_up_model, args=(dict(self._cfg),), daemon=True).start()

        # Open a lightweight control panel instead of relying on terminal output.
        self._open_control_panel()

        # Run tray in main thread (blocking)
        self._tray = TrayApp(
            on_toggle=self._toggle_active,
            on_settings=self._open_control_panel,
            on_quit=self._quit,
            is_active=lambda: self._active,
        )
        self._tray.run()

    def _on_key_press(self) -> None:
        if not self._active or self._transcribing:
            return
        log.info("Key pressed - start recording")
        self._hud.show(HudState.LISTENING)
        self._write_status(HudState.LISTENING, "Recording")
        self._recorder.start()

    def _on_key_release(self) -> None:
        if not self._recorder.is_recording:
            return
        log.info("Key released - stop recording, transcribe")
        self._hud.show(HudState.TRANSCRIBING)

        wav_path = self._recorder.stop()
        if wav_path is None:
            log.warning("Recording too short")
            self._hud.show(HudState.ERROR, "Too short")
            self._write_status(HudState.ERROR, "Too short")
            return

        # Transcribe in background thread
        self._transcribing = True
        self._write_status(HudState.TRANSCRIBING, "Transcribing")
        threading.Thread(target=self._do_transcribe, args=(wav_path,), daemon=True).start()

    def _do_transcribe(self, wav_path: str) -> None:
        try:
            text = transcribe(wav_path, self._cfg)
            if not text:
                self._hud.show(HudState.ERROR, "No speech detected")
                self._write_status(HudState.ERROR, "No speech detected")
                return

            auto_paste = self._cfg.get("auto_paste", True)
            copy_and_paste(text, auto_paste=auto_paste)

            # Save last transcript
            config.LAST_TRANSCRIPT_PATH.write_text(text, encoding="utf-8")
            self._append_transcript_history(text)

            self._hud.show(HudState.DONE)
            self._write_status(HudState.DONE, text)
            log.info("Done: %s", text[:80])
        except Exception:
            log.exception("Transcription failed")
            self._hud.show(HudState.ERROR, "Error")
            self._write_status(HudState.ERROR, "Transcription failed")
        finally:
            self._transcribing = False
            # Clean up wav
            try:
                os.remove(wav_path)
            except OSError:
                pass

    def _toggle_active(self) -> None:
        self._active = not self._active
        if self._active:
            self._hotkey.start()
            log.info("Resumed")
            self._write_status(HudState.HIDDEN, "Ready")
        else:
            self._hotkey.stop()
            log.info("Paused")
            self._write_status(HudState.HIDDEN, "Paused")

    def _open_control_panel(self, blocking: bool = False) -> None:
        def on_save(new_cfg: dict):
            old_model = self._cfg.get("model")
            old_gpu_enabled = self._cfg.get("gpu_enabled", True)
            self._cfg = new_cfg
            config.save(new_cfg)

            # Update hotkey
            if self._hotkey:
                self._hotkey.update_hotkey(new_cfg.get("hotkey", "Key.alt_r"))

            # Reload model if changed
            if new_cfg.get("model") != old_model or new_cfg.get("gpu_enabled", True) != old_gpu_enabled:
                unload_model()
                threading.Thread(target=warm_up_model, args=(dict(self._cfg),), daemon=True).start()

            log.info("Settings saved")
            self._write_status(HudState.HIDDEN, "Settings saved")

        win = SettingsWindow(self._cfg, on_save)
        win.show(blocking=blocking)

    def _quit(self) -> None:
        log.info("Quitting...")
        self._write_status(HudState.HIDDEN, "Quitting")
        if self._hotkey:
            self._hotkey.stop()
        self._hud.stop()
        if self._tray:
            self._tray.stop()
        self._release_single_instance()

    def _acquire_single_instance(self) -> bool:
        current_pid = os.getpid()

        try:
            if config.PID_PATH.exists():
                other_pid = int(config.PID_PATH.read_text(encoding="utf-8").strip())
                if other_pid != current_pid:
                    try:
                        os.kill(other_pid, 0)
                    except OSError:
                        pass
                    else:
                        return False
            config.PID_PATH.write_text(str(current_pid), encoding="utf-8")
            return True
        except OSError:
            log.exception("Failed to create PID file")
            return True

    def _release_single_instance(self) -> None:
        try:
            if config.PID_PATH.exists():
                pid_text = config.PID_PATH.read_text(encoding="utf-8").strip()
                if pid_text == str(os.getpid()):
                    config.PID_PATH.unlink()
        except OSError:
            log.exception("Failed to remove PID file")

    def _append_transcript_history(self, text: str) -> None:
        entries = []
        if config.TRANSCRIPT_HISTORY_PATH.exists():
            try:
                entries = json.loads(config.TRANSCRIPT_HISTORY_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []

        entries.insert(0, {
            "text": text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        config.TRANSCRIPT_HISTORY_PATH.write_text(
            json.dumps(entries[:20], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_status(self, state: str, detail: str) -> None:
        payload = {
            "app_name": config.APP_NAME,
            "active": self._active,
            "transcribing": self._transcribing,
            "state": state,
            "detail": detail,
            "hotkey": self._cfg.get("hotkey", "Fn" if sys.platform == "darwin" else "Key.alt_r"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            config.STATUS_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            log.exception("Failed to write status file")


def main():
    app = VoiceInputApp()
    app.run()


if __name__ == "__main__":
    main()
