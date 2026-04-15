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
        "fn":            (63, 0x800000),   # NSEventModifierFlagSecondaryFn
        "Key.alt_r":     (61, 0x80000),    # NSEventModifierFlagOption
        "Key.alt_l":     (58, 0x80000),    # NSEventModifierFlagOption
        "Key.cmd_r":     (54, 0x100000),   # NSEventModifierFlagCommand
        "Key.cmd_l":     (55, 0x100000),   # NSEventModifierFlagCommand
        "Key.ctrl_l":    (59, 0x40000),    # NSEventModifierFlagControl
        "Key.ctrl_r":    (62, 0x40000),    # NSEventModifierFlagControl
        "Key.shift_l":   (56, 0x20000),    # NSEventModifierFlagShift
        "Key.shift_r":   (60, 0x20000),    # NSEventModifierFlagShift
        "Key.caps_lock": (57, 0x10000),    # NSEventModifierFlagCapsLock
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
        self._is_modifier = hotkey_str in self._KEY_MAP
        if self._is_modifier:
            self._keycode, self._flag = self._KEY_MAP[hotkey_str]
        else:
            # Normal key — resolve keycode from char
            self._keycode = self._char_to_keycode(hotkey_str)
            self._flag = 0
        log.info("MacHotkeyListener init: key=%s keycode=%d modifier=%s",
                 hotkey_str, self._keycode, self._is_modifier)

    @staticmethod
    def _char_to_keycode(char):
        """Map a character to macOS virtual keycode."""
        _CHAR_MAP = {
            'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5,
            'h': 4, 'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45,
            'o': 31, 'p': 35, 'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32,
            'v': 9, 'w': 13, 'x': 7, 'y': 16, 'z': 6,
            '1': 18, '2': 19, '3': 20, '4': 21, '5': 23,
            '6': 22, '7': 26, '8': 28, '9': 25, '0': 29,
        }
        # Handle Key.f1-Key.f12
        if char.startswith("Key.f") and char[5:].isdigit():
            fnum = int(char[5:])
            f_codes = {1:122, 2:120, 3:99, 4:118, 5:96, 6:97,
                       7:98, 8:100, 9:101, 10:109, 11:103, 12:111}
            return f_codes.get(fnum, 122)
        _SPECIAL = {
            "Key.esc": 53, "space": 49, "return": 36, "tab": 48,
            "delete": 51, "forward_delete": 117,
            "left": 123, "right": 124, "down": 125, "up": 126,
        }
        if char in _SPECIAL:
            return _SPECIAL[char]
        if char.startswith("Key.esc"):
            return 53
        # Try as raw keycode (e.g. "18" from old config)
        if char.isdigit() and int(char) > 9:
            return int(char)
        return _CHAR_MAP.get(char.lower(), 0)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        import Quartz

        keycode = self._keycode
        flag = self._flag
        is_modifier = self._is_modifier

        def callback(proxy, event_type, event, refcon):
            # Re-enable tap if macOS disabled it
            if event_type not in (Quartz.kCGEventFlagsChanged,
                                   Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
                try:
                    if self._tap:
                        Quartz.CGEventTapEnable(self._tap, True)
                except Exception:
                    pass
                return event

            ev_keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)

            if is_modifier:
                # Modifier key: use FlagsChanged
                if event_type == Quartz.kCGEventFlagsChanged and ev_keycode == keycode:
                    flags = Quartz.CGEventGetFlags(event)
                    key_pressed = bool(flags & flag)
                    if key_pressed and not self._key_down:
                        self._key_down = True
                        try: self._on_press()
                        except Exception: log.exception("Error in on_press")
                    elif not key_pressed and self._key_down:
                        self._key_down = False
                        try: self._on_release()
                        except Exception: log.exception("Error in on_release")
            else:
                # Normal key: use KeyDown/KeyUp
                if ev_keycode == keycode:
                    if event_type == Quartz.kCGEventKeyDown and not self._key_down:
                        self._key_down = True
                        try: self._on_press()
                        except Exception: log.exception("Error in on_press")
                    elif event_type == Quartz.kCGEventKeyUp and self._key_down:
                        self._key_down = False
                        try: self._on_release()
                        except Exception: log.exception("Error in on_release")

            return event

        event_mask = (Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
                      | Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                      | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp))
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
