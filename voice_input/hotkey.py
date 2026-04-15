"""Global hotkey listener - Mac: Quartz CGEventTap (configurable modifier), Windows: pynput."""

import logging
import sys
import threading
from typing import Callable

log = logging.getLogger(__name__)


class HotkeyListener:
    """Cross-platform hotkey listener."""

    def __init__(
        self,
        hotkey_str: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ):
        self._hotkey_str = hotkey_str
        self._on_press = on_press
        self._on_release = on_release
        self._running = False
        self._impl = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        if sys.platform == "darwin":
            self._impl = _MacHotkeyListener(self._hotkey_str, self._on_press, self._on_release)
        else:
            self._impl = _PynputListener(self._hotkey_str, self._on_press, self._on_release)

        self._impl.start()
        log.info("Hotkey listener started (%s)", self._hotkey_str)

    def stop(self) -> None:
        self._running = False
        if self._impl:
            self._impl.stop()
            self._impl = None
        log.info("Hotkey listener stopped")

    def update_hotkey(self, hotkey_str: str) -> None:
        if hotkey_str == self._hotkey_str:
            return
        log.info("Updating hotkey from %s to %s", self._hotkey_str, hotkey_str)
        self._hotkey_str = hotkey_str
        if self._running and self._impl:
            if sys.platform == "darwin":
                # Must fully stop + restart on macOS (CGEventTap captures keycode at creation)
                self._impl.stop()
                self._impl = _MacHotkeyListener(self._hotkey_str, self._on_press, self._on_release)
                self._impl.start()
                log.info("Hotkey listener restarted for %s", hotkey_str)
            elif hasattr(self._impl, "update_hotkey"):
                self._impl.update_hotkey(hotkey_str)


class _MacHotkeyListener:
    """Listen for configurable modifier key on macOS using Quartz CGEventTap."""

    # keycode → modifier flag mask (NSEvent modifier flags)
    _KEY_MAP = {
        "fn":          (63, 0x800000),   # NSEventModifierFlagSecondaryFn
        "Key.alt_r":   (61, 0x80000),    # NSEventModifierFlagOption
        "Key.cmd_r":   (54, 0x100000),   # NSEventModifierFlagCommand
        "Key.ctrl_l":  (59, 0x40000),    # NSEventModifierFlagControl
    }

    def __init__(self, hotkey_str, on_press, on_release):
        self._hotkey_str = hotkey_str
        self._on_press = on_press
        self._on_release = on_release
        self._key_down = False
        self._thread = None
        self._tap = None
        self._loop_ref = None
        self._source = None
        self._keycode, self._flag = self._KEY_MAP.get(hotkey_str, (63, 0x800000))
        log.info("MacHotkeyListener init: key=%s keycode=%d flag=0x%x",
                 hotkey_str, self._keycode, self._flag)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        import Quartz

        keycode = self._keycode
        flag = self._flag

        def callback(proxy, event_type, event, refcon):
            # Re-enable tap if macOS disabled it
            if event_type != Quartz.kCGEventFlagsChanged:
                try:
                    if self._tap:
                        Quartz.CGEventTapEnable(self._tap, True)
                except Exception:
                    pass
                return event

            ev_keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            flags = Quartz.CGEventGetFlags(event)

            if ev_keycode == keycode:
                key_pressed = bool(flags & flag)
                if key_pressed and not self._key_down:
                    self._key_down = True
                    try:
                        self._on_press()
                    except Exception:
                        log.exception("Error in on_press")
                elif not key_pressed and self._key_down:
                    self._key_down = False
                    try:
                        self._on_release()
                    except Exception:
                        log.exception("Error in on_release")

            return event

        event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            event_mask,
            callback,
            None,
        )

        if self._tap is None:
            log.error("Failed to create event tap for %s. "
                      "Grant Accessibility permissions in System Settings.", self._hotkey_str)
            return

        self._source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        self._loop_ref = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(self._loop_ref, self._source, Quartz.kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self._tap, True)
        log.info("Event tap active for %s (keycode=%d, flag=0x%x)", self._hotkey_str, keycode, flag)
        Quartz.CFRunLoopRun()
        log.info("Event tap run loop exited for %s", self._hotkey_str)

    def stop(self) -> None:
        self._key_down = False

        # Stop run loop first (unblocks the thread)
        if self._loop_ref:
            try:
                import Quartz
                Quartz.CFRunLoopStop(self._loop_ref)
            except Exception:
                pass

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        # Now disable and clean up tap (thread is done, safe to access)
        if self._tap:
            try:
                import Quartz
                Quartz.CGEventTapEnable(self._tap, False)
            except Exception:
                pass

        self._tap = None
        self._source = None
        self._loop_ref = None
        self._thread = None
        log.info("Event tap stopped for %s", self._hotkey_str)


class _PynputListener:
    """Listen for configurable key on Windows using pynput."""

    def __init__(self, hotkey_str, on_press, on_release):
        from pynput import keyboard

        self._target_key = self._resolve_key(hotkey_str)
        self._on_press = on_press
        self._on_release = on_release
        self._listener = None
        self._key_down = False

    @staticmethod
    def _resolve_key(key_str):
        from pynput import keyboard

        if key_str.startswith("Key."):
            return getattr(keyboard.Key, key_str[4:])
        if len(key_str) == 1:
            return keyboard.KeyCode.from_char(key_str)
        return getattr(keyboard.Key, key_str)

    def start(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._key_down = False

    def update_hotkey(self, hotkey_str):
        self._target_key = self._resolve_key(hotkey_str)

    def _handle_press(self, key):
        if self._key_down:
            return
        if key == self._target_key:
            self._key_down = True
            try:
                self._on_press()
            except Exception:
                log.exception("Error in on_press")

    def _handle_release(self, key):
        if not self._key_down:
            return
        if key == self._target_key:
            self._key_down = False
            try:
                self._on_release()
            except Exception:
                log.exception("Error in on_release")
