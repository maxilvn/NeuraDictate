"""Global hotkey listener - Mac: Quartz CGEventTap (configurable modifier), Windows: pynput."""

import logging
import sys
import threading
from typing import Callable

log = logging.getLogger(__name__)


class HotkeyListener:
    """Cross-platform hotkey listener. On Mac uses Fn via Quartz, on Windows uses pynput."""

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
        self._hotkey_str = hotkey_str
        if self._running and self._impl:
            if sys.platform == "darwin":
                self._impl.stop()
                self._impl = _MacHotkeyListener(self._hotkey_str, self._on_press, self._on_release)
                self._impl.start()
            elif hasattr(self._impl, "update_hotkey"):
                self._impl.update_hotkey(hotkey_str)


class _MacHotkeyListener:
    """Listen for configurable modifier key on macOS using Quartz CGEventTap."""

    # keycode, modifier flag mask (from NSEvent modifier flags)
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
        self._keycode, self._flag = self._KEY_MAP.get(hotkey_str, (63, 0x800000))

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        import Quartz
        from Foundation import NSRunLoop, NSDate

        keycode = self._keycode
        flag = self._flag

        def callback(proxy, event_type, event, refcon):
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
            log.error("Failed to create event tap. Grant Accessibility permissions in System Settings.")
            return

        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        self._loop_ref = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(self._loop_ref, source, Quartz.kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self._tap, True)
        Quartz.CFRunLoopRun()

    def stop(self) -> None:
        self._key_down = False
        if self._loop_ref:
            import Quartz
            Quartz.CFRunLoopStop(self._loop_ref)
            self._loop_ref = None


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
