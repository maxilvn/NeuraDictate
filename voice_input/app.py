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
from .transcriber import transcribe, unload_model, warm_up_model, download_model, delete_model
from .tray import TrayApp

_log_fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_root = logging.getLogger()
_root.setLevel(logging.INFO)
# Avoid duplicate handlers on re-import
if not _root.handlers:
    _root.addHandler(logging.StreamHandler())
    _fh = logging.FileHandler(config.LOG_PATH, encoding="utf-8")
    _fh.setFormatter(logging.Formatter(_log_fmt))
    _root.addHandler(_fh)
for _h in _root.handlers:
    _h.setFormatter(logging.Formatter(_log_fmt))
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
        self._cancel_transcription = False
        self._panel_open = False

    def run(self) -> None:
        if not self._acquire_single_instance():
            log.info("Another instance is already running; signaling it to open panel")
            # Signal the running instance to open its panel
            try:
                signal_path = config.CACHE_DIR / "open_panel"
                signal_path.write_text("1")
            except OSError:
                pass
            return

        log.info("%s starting...", config.APP_NAME)
        self._write_status(HudState.HIDDEN, "Starting")

        # Clear transcript history for fresh session
        try:
            config.TRANSCRIPT_HISTORY_PATH.write_text("[]", encoding="utf-8")
        except OSError:
            pass

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

        # Start config watcher for live settings updates
        self._start_config_watcher()

        # Open a lightweight control panel instead of relying on terminal output.
        self._open_control_panel()

        # Run tray in main thread (blocking)
        log.info("Starting tray icon...")
        try:
            self._tray = TrayApp(
                on_toggle=self._toggle_active,
                on_settings=self._open_control_panel,
                on_quit=self._quit,
                is_active=lambda: self._active,
            )
            log.info("Tray created, running...")
            self._tray.run()
        except Exception:
            log.exception("Tray failed")

    def _on_key_press(self) -> None:
        if not self._active:
            return
        if self._transcribing:
            # Cancel current transcription and start fresh
            log.info("Key pressed during transcription - cancelling and restarting")
            self._cancel_transcription = True
            self._transcribing = False
        log.info("Key pressed (%s) - start recording", config.HOTKEY_OPTIONS.get(self._cfg.get("hotkey"), "?"))
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
        self._cancel_transcription = False
        self._write_status(HudState.TRANSCRIBING, "Transcribing")
        threading.Thread(target=self._do_transcribe, args=(wav_path,), daemon=True).start()

    def _do_transcribe(self, wav_path: str) -> None:
        try:
            # Timeout guard: run transcription in a sub-thread
            result = [None]
            def _run():
                result[0] = transcribe(wav_path, self._cfg)
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout=30)
            if self._cancel_transcription:
                log.info("Transcription cancelled")
                return
            if t.is_alive():
                log.error("Transcription timed out after 30s")
                self._hud.show(HudState.ERROR, "Timeout")
                self._write_status(HudState.ERROR, "Transcription timed out")
                return
            text = result[0]
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
        if not self._hotkey:
            return
        self._active = not self._active
        self._transcribing = False
        if self._active:
            self._hotkey.start()
            log.info("Resumed")
            self._write_status(HudState.HIDDEN, "Ready")
        else:
            self._hotkey.stop()
            log.info("Paused")
            self._write_status(HudState.HIDDEN, "Paused")

    def _start_config_watcher(self) -> None:
        """Poll config.json every 2s for live changes from settings window."""
        self._config_mtime = 0
        try:
            if config.CONFIG_PATH.exists():
                self._config_mtime = config.CONFIG_PATH.stat().st_mtime
        except OSError:
            pass

        def watch():
            signal_path = config.CACHE_DIR / "open_panel"
            while True:
                import time
                time.sleep(2)
                try:
                    # Check if another instance wants us to open the panel
                    if signal_path.exists():
                        signal_path.unlink()
                        self._open_control_panel()
                    if not config.CONFIG_PATH.exists():
                        continue
                    mtime = config.CONFIG_PATH.stat().st_mtime
                    if mtime > self._config_mtime:
                        self._config_mtime = mtime
                        new_cfg = config.load()
                        self._apply_config(new_cfg)
                except Exception:
                    log.exception("Config watcher error")

        threading.Thread(target=watch, daemon=True).start()

    def _apply_config(self, new_cfg: dict) -> None:
        """Apply config changes (hotkey, model, etc)."""
        old_hotkey = self._cfg.get("hotkey")
        old_model = self._cfg.get("model")
        self._cfg = new_cfg

        default_hotkey = "fn" if sys.platform == "darwin" else "Key.alt_r"
        if new_cfg.get("hotkey") != old_hotkey and self._hotkey:
            self._hotkey.update_hotkey(new_cfg.get("hotkey", default_hotkey))

        if new_cfg.get("model") != old_model:
            unload_model()
            threading.Thread(target=warm_up_model, args=(dict(self._cfg),), daemon=True).start()

        log.info("Config applied: hotkey=%s model=%s language=%s", new_cfg.get("hotkey"), new_cfg.get("model"), new_cfg.get("language"))
        self._write_status(HudState.HIDDEN, "Settings saved")

    def _open_control_panel(self, blocking: bool = False) -> None:
        # If a panel is already open, just focus it instead of opening a second
        if SettingsWindow.is_open() and not blocking:
            SettingsWindow.focus_existing()
            return

        def on_save(new_cfg: dict):
            self._panel_open = False
            # Update mtime so the watcher doesn't re-apply the same change
            try:
                if config.CONFIG_PATH.exists():
                    self._config_mtime = config.CONFIG_PATH.stat().st_mtime
            except OSError:
                pass
            self._apply_config(new_cfg)

        self._panel_open = True
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
            "hotkey": config.HOTKEY_OPTIONS.get(self._cfg.get("hotkey", "fn"), self._cfg.get("hotkey", "fn")),
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
