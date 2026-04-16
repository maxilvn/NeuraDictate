"""HUD overlay - minimal floating pill at bottom-center. Mac: AppKit, Windows: tkinter."""

import sys
import threading


class HudState:
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    ERROR = "error"
    HIDDEN = "hidden"


# Subtle, muted colors
_COLORS = {
    HudState.LISTENING: ("#FFFFFF", "#1C1C1E"),     # White bg, black text
    HudState.TRANSCRIBING: ("#FFFFFF", "#1C1C1E"),  # White bg, black text
    HudState.DONE: ("#FFFFFF", "#1C1C1E"),           # White bg, black text
    HudState.ERROR: ("#FFFFFF", "#FF3B30"),          # White bg, red text
}

_LABELS = {
    HudState.LISTENING: "Listening",
    HudState.TRANSCRIBING: "Transcribing",
    HudState.DONE: "Copied",
    HudState.ERROR: "Error",
}

# Small dot indicators
_DOTS = {
    HudState.LISTENING: "#34C759",
    HudState.TRANSCRIBING: "#1C1C1E",
    HudState.DONE: "#34C759",
    HudState.ERROR: "#FF3B30",
}

PILL_WIDTH = 150
PILL_HEIGHT = 30
BOTTOM_MARGIN = 60
DOT_SIZE = 8
DOT_GAP = 8
PILL_HORIZONTAL_PADDING = 36


class HudOverlay:
    def __init__(self):
        self._impl = None

    def start(self) -> None:
        if sys.platform == "darwin":
            self._impl = _MacHud()
        else:
            self._impl = _TkHud()
        self._impl.start()

    def show(self, state, message=None):
        if self._impl:
            self._impl.show(state, message)

    def hide(self) -> None:
        if self._impl:
            self._impl.hide()

    def stop(self) -> None:
        if self._impl:
            self._impl.stop()


class _MacHud:
    """Native macOS floating pill using AppKit/PyObjC."""

    def __init__(self):
        self._panel = None
        self._label = None
        self._dot_label = None
        self._icon_view = None
        self._hide_timer = None
        self._pulse_timer = None
        self._pulse_growing = True
        self._pulse_size = 14
        self._font = None
        self._dot_font = None
        self._label_height = None
        self._dot_width = None
        self._current_state = None
        self._neura_icon = None

    def start(self) -> None:
        pass

    def _ensure_panel(self):
        if self._panel is not None:
            return

        import AppKit

        screen = AppKit.NSScreen.mainScreen().frame()
        x = (screen.size.width - PILL_WIDTH) / 2
        y = BOTTOM_MARGIN

        self._panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((x, y), (PILL_WIDTH, PILL_HEIGHT)),
            AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self._panel.setLevel_(AppKit.NSFloatingWindowLevel + 1)
        self._panel.setOpaque_(False)
        self._panel.setBackgroundColor_(AppKit.NSColor.clearColor())
        self._panel.setAlphaValue_(0.98)
        self._panel.setHasShadow_(True)
        self._panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
        )

        content = self._panel.contentView()
        content.setWantsLayer_(True)
        content.layer().setCornerRadius_(PILL_HEIGHT / 2)
        content.layer().setMasksToBounds_(True)

        # Load Neura icon for transcribing state
        from pathlib import Path
        icon_path = str(Path(__file__).resolve().parent.parent / "icon.png")
        self._neura_icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
        self._font = AppKit.NSFont.systemFontOfSize_weight_(12, 0.3)
        self._dot_font = AppKit.NSFont.systemFontOfSize_weight_(13, 0.5)
        self._label_height = self._font.ascender() - self._font.descender() + self._font.leading() + 4
        self._dot_width = 10

    def _rebuild_views(self):
        import AppKit

        content = self._panel.contentView()
        for subview in list(content.subviews()):
            subview.removeFromSuperview()

        self._dot_label = AppKit.NSTextField.labelWithString_("●")
        self._dot_label.setBezeled_(False)
        self._dot_label.setDrawsBackground_(False)
        self._dot_label.setEditable_(False)
        self._dot_label.setSelectable_(False)
        self._dot_label.setAlignment_(AppKit.NSTextAlignmentLeft)

        self._label = AppKit.NSTextField.labelWithString_("")
        self._label.setBezeled_(False)
        self._label.setDrawsBackground_(False)
        self._label.setEditable_(False)
        self._label.setSelectable_(False)
        self._label.setAlignment_(AppKit.NSTextAlignmentLeft)

        label_y = (PILL_HEIGHT - self._label_height) / 2
        self._dot_label.setFrame_(((0, label_y), (self._dot_width, self._label_height)))
        self._label.setFrame_(((0, label_y), (PILL_WIDTH, self._label_height)))
        content.addSubview_(self._dot_label)
        content.addSubview_(self._label)

    def show(self, state, message=None):
        import AppKit

        def _do_show():
            self._ensure_panel()
            self._rebuild_views()
            from Foundation import NSAttributedString

            if self._hide_timer:
                self._hide_timer.invalidate()
                self._hide_timer = None
            if self._pulse_timer:
                self._pulse_timer.invalidate()
                self._pulse_timer = None

            self._current_state = state
            bg_hex, fg_hex = _COLORS.get(state, _COLORS[HudState.ERROR])
            dot_hex = _DOTS.get(state, _DOTS[HudState.ERROR])
            text = message or _LABELS.get(state, state)

            bg = _hex_to_nscolor(bg_hex)
            fg = _hex_to_nscolor(fg_hex)
            dot_color = _hex_to_nscolor(dot_hex)

            text_str = NSAttributedString.alloc().initWithString_attributes_(
                text, {
                    AppKit.NSFontAttributeName: self._font,
                    AppKit.NSForegroundColorAttributeName: fg,
                }
            )
            text_size = text_str.size()
            icon_s = 16
            content_w = icon_s + DOT_GAP + text_size.width

            self._panel.contentView().layer().setBackgroundColor_(bg.CGColor())

            # Always show Neura icon instead of dot
            self._dot_label.setStringValue_("")
            if self._icon_view:
                self._icon_view.removeFromSuperview()
            self._icon_view = AppKit.NSImageView.alloc().initWithFrame_(
                ((0, 0), (icon_s, icon_s)))
            if self._neura_icon:
                self._icon_view.setImage_(self._neura_icon)
            self._icon_view.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
            self._panel.contentView().addSubview_(self._icon_view)

            self._label.setStringValue_(text)
            self._label.setTextColor_(fg)
            self._label.setFont_(self._font)

            pill_w = content_w + PILL_HORIZONTAL_PADDING
            screen = AppKit.NSScreen.mainScreen().frame()
            x = (screen.size.width - pill_w) / 2
            self._panel.setFrame_display_(((x, BOTTOM_MARGIN), (pill_w, PILL_HEIGHT)), True)
            content_x = (pill_w - content_w) / 2
            icon_y = (PILL_HEIGHT - icon_s) / 2
            self._icon_view.setFrame_(((content_x, icon_y), (icon_s, icon_s)))
            label_y = (PILL_HEIGHT - self._label_height) / 2
            self._label.setFrame_(((content_x + icon_s + DOT_GAP, label_y), (text_size.width + 2, self._label_height)))
            self._panel.contentView().setNeedsDisplay_(True)
            self._dot_label.setNeedsDisplay_(True)
            self._label.setNeedsDisplay_(True)
            self._panel.display()
            self._panel.orderFront_(None)

            if state == HudState.LISTENING and self._icon_view:
                # Gentle breathing animation (opacity pulse)
                self._pulse_growing = False
                self._pulse_alpha = 1.0
                def _breathe(_):
                    if self._current_state != HudState.LISTENING or not self._icon_view:
                        return
                    if self._pulse_growing:
                        self._pulse_alpha += 0.06
                        if self._pulse_alpha >= 1.0:
                            self._pulse_alpha = 1.0
                            self._pulse_growing = False
                    else:
                        self._pulse_alpha -= 0.06
                        if self._pulse_alpha <= 0.3:
                            self._pulse_alpha = 0.3
                            self._pulse_growing = True
                    self._icon_view.setAlphaValue_(self._pulse_alpha)
                self._pulse_timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                    0.05, True, _breathe)

            elif state == HudState.TRANSCRIBING and self._icon_view:
                # Smooth size pulse using sin() for no jumping
                import math
                self._pulse_t = 0.0
                _base_s = float(icon_s)
                _cx = content_x + icon_s / 2  # center x
                _cy = PILL_HEIGHT / 2          # center y
                def _pulse(_):
                    if self._current_state != HudState.TRANSCRIBING or not self._icon_view:
                        return
                    self._pulse_t += 0.10
                    s = _base_s + math.sin(self._pulse_t) * 3
                    self._icon_view.setFrame_(((_cx - s/2, _cy - s/2), (s, s)))
                    self._icon_view.setNeedsDisplay_(True)
                self._pulse_timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                    0.03, True, _pulse)

            if state in (HudState.DONE, HudState.ERROR):
                self._hide_timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                    1.5, False, lambda _: self.hide()
                )

        if threading.current_thread() is threading.main_thread():
            _do_show()
        else:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(_do_show)

    def hide(self) -> None:
        def _do_hide():
            if self._pulse_timer:
                self._pulse_timer.invalidate()
                self._pulse_timer = None
            self._current_state = None
            if self._panel:
                self._panel.orderOut_(None)

        if threading.current_thread() is threading.main_thread():
            _do_hide()
        else:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(_do_hide)

    def stop(self) -> None:
        self.hide()


class _TkHud:
    """Windows HUD - white pill with Neura icon + animations."""

    ICON_SIZE = 16

    def __init__(self):
        self._root = None
        self._canvas = None
        self._text_id = None
        self._icon_id = None
        self._icon_img = None
        self._hide_timer = None
        self._anim_timer = None
        self._current_state = None
        self._ready = threading.Event()

    def start(self) -> None:
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        self._ready.wait(timeout=5)

    def _run(self) -> None:
        import tkinter as tk
        from pathlib import Path

        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.95)
        TRANS = "#F0F0F0"
        self._root.config(bg=TRANS)
        try:
            self._root.attributes("-transparentcolor", TRANS)
        except tk.TclError:
            pass
        self._root.withdraw()

        self._canvas = tk.Canvas(
            self._root, width=PILL_WIDTH, height=PILL_HEIGHT,
            bg=TRANS, highlightthickness=0, bd=0
        )
        self._canvas.pack()

        # Rounded pill background
        r = PILL_HEIGHT // 2
        self._canvas.create_arc(0, 0, PILL_HEIGHT, PILL_HEIGHT, start=90, extent=180, fill="#FFFFFF", outline="")
        self._canvas.create_arc(PILL_WIDTH - PILL_HEIGHT, 0, PILL_WIDTH, PILL_HEIGHT, start=-90, extent=180, fill="#FFFFFF", outline="")
        self._canvas.create_rectangle(r, 0, PILL_WIDTH - r, PILL_HEIGHT, fill="#FFFFFF", outline="")

        # Load Neura icon
        icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        try:
            self._icon_img = tk.PhotoImage(file=str(icon_path))
            # Scale to ICON_SIZE
            sw = max(1, self._icon_img.width() // self.ICON_SIZE)
            if sw > 1:
                self._icon_img = self._icon_img.subsample(sw, sw)
        except Exception:
            self._icon_img = None

        # Icon
        icon_x = 18
        icon_y = PILL_HEIGHT // 2
        if self._icon_img:
            self._icon_id = self._canvas.create_image(icon_x, icon_y, image=self._icon_img)
        else:
            self._icon_id = self._canvas.create_oval(
                14, (PILL_HEIGHT - DOT_SIZE) // 2, 14 + DOT_SIZE,
                (PILL_HEIGHT + DOT_SIZE) // 2, fill="#34C759", outline="")

        # Text
        self._text_id = self._canvas.create_text(
            32, PILL_HEIGHT // 2, anchor="w",
            text="", fill="#1C1C1E", font=("Segoe UI", 10)
        )

        self._ready.set()
        self._root.mainloop()

    def show(self, state, message=None):
        if self._root is None:
            return

        def _update():
            if self._root is None:
                return
            if self._hide_timer:
                self._root.after_cancel(self._hide_timer)
                self._hide_timer = None
            if self._anim_timer:
                self._root.after_cancel(self._anim_timer)
                self._anim_timer = None

            self._current_state = state
            _, fg = _COLORS.get(state, _COLORS[HudState.ERROR])
            text = message or _LABELS.get(state, state)

            self._canvas.itemconfig(self._text_id, text=text, fill=fg)
            self._canvas.update_idletasks()

            # Center icon + text
            text_bbox = self._canvas.bbox(self._text_id)
            text_w = (text_bbox[2] - text_bbox[0]) if text_bbox else 0
            ics = self.ICON_SIZE
            content_w = ics + DOT_GAP + text_w
            cx = max(0, (PILL_WIDTH - content_w) / 2)
            self._canvas.coords(self._text_id, cx + ics + DOT_GAP, PILL_HEIGHT / 2)

            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            x = (screen_w - PILL_WIDTH) // 2
            y = screen_h - PILL_HEIGHT - BOTTOM_MARGIN
            self._root.geometry(f"{PILL_WIDTH}x{PILL_HEIGHT}+{x}+{y}")
            self._root.deiconify()

            # Animations
            if state == HudState.LISTENING:
                self._start_breathing()
            elif state == HudState.TRANSCRIBING:
                self._start_pulsing()

            if state in (HudState.DONE, HudState.ERROR):
                self._hide_timer = self._root.after(1500, self.hide)

        self._root.after(0, _update)

    def _start_breathing(self):
        """Opacity breathing for listening."""
        self._breath_alpha = 1.0
        self._breath_dir = -1
        def _breathe():
            if self._current_state != HudState.LISTENING or not self._root:
                return
            self._breath_alpha += self._breath_dir * 0.06
            if self._breath_alpha <= 0.3:
                self._breath_dir = 1
            elif self._breath_alpha >= 1.0:
                self._breath_dir = -1
            try:
                self._root.attributes("-alpha", self._breath_alpha * 0.95)
            except Exception:
                pass
            self._anim_timer = self._root.after(50, _breathe)
        _breathe()

    def _start_pulsing(self):
        """Size pulsing for transcribing via window alpha."""
        import math
        self._pulse_t = 0.0
        def _pulse():
            if self._current_state != HudState.TRANSCRIBING or not self._root:
                return
            self._pulse_t += 0.10
            alpha = 0.5 + 0.45 * math.sin(self._pulse_t)
            try:
                self._root.attributes("-alpha", alpha)
            except Exception:
                pass
            self._anim_timer = self._root.after(30, _pulse)
        _pulse()

    def hide(self) -> None:
        if self._root:
            def _do_hide():
                if self._anim_timer:
                    self._root.after_cancel(self._anim_timer)
                    self._anim_timer = None
                self._current_state = None
                try:
                    self._root.attributes("-alpha", 0.95)
                except Exception:
                    pass
                self._root.withdraw()
            self._root.after(0, _do_hide)

    def stop(self) -> None:
        if self._root:
            def _do_stop():
                if self._hide_timer:
                    self._root.after_cancel(self._hide_timer)
                if self._anim_timer:
                    self._root.after_cancel(self._anim_timer)
                self._root.destroy()
            self._root.after(0, _do_stop)
            self._root = None


def _hex_to_nscolor(hex_str: str):
    import AppKit
    r = int(hex_str[1:3], 16) / 255.0
    g = int(hex_str[3:5], 16) / 255.0
    b = int(hex_str[5:7], 16) / 255.0
    return AppKit.NSColor.colorWithRed_green_blue_alpha_(r, g, b, 1.0)
