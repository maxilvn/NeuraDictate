"""System tray icon with menu - cross-platform."""

import sys
from typing import Callable

from . import config


def _create_tray(on_toggle, on_settings, on_quit, is_active):
    if sys.platform == "darwin":
        return _MacTray(on_toggle, on_settings, on_quit, is_active)
    return _WinTray(on_toggle, on_settings, on_quit, is_active)


class _MacTray:
    """macOS tray using rumps (native Cocoa)."""

    def __init__(self, on_toggle, on_settings, on_quit, is_active):
        import rumps

        self._on_toggle = on_toggle
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._is_active = is_active
        icon_path = str(config.MODULE_DIR.parent / "icon.png")
        try:
            self._app = rumps.App(config.APP_NAME, title="", icon=icon_path, template=True, quit_button=None)
        except Exception:
            self._app = rumps.App(config.APP_NAME, title="N", quit_button=None)

    def run(self) -> None:
        import rumps

        # Bind callbacks via MenuItem objects — more reliable than @rumps.clicked
        # decorators which require the method to be on the App subclass.
        def _toggle(_):
            try:
                self._on_toggle()
            except Exception:
                import traceback
                traceback.print_exc()

        def _settings(_):
            try:
                self._on_settings()
            except Exception:
                import traceback
                traceback.print_exc()

        def _quit_app(_):
            try:
                self._on_quit()
            except Exception:
                pass
            rumps.quit_application()

        self._app.menu = [
            rumps.MenuItem("Control Panel", callback=_settings),
            None,
            rumps.MenuItem("Quit", callback=_quit_app),
        ]

        # Install reopen-event handler so dock/Finder clicks open settings
        self._install_reopen_handler()

        self._app.run()

    def _install_reopen_handler(self):
        """When user clicks app icon in Dock/Applications while running, open settings."""
        try:
            import AppKit
            from PyObjCTools.AppHelper import callAfter

            _on_settings = self._on_settings

            class _ReopenDelegate(AppKit.NSObject):
                def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_visible):
                    try:
                        _on_settings()
                    except Exception:
                        pass
                    return False

            # rumps sets up its own delegate. We wrap it.
            nsapp = AppKit.NSApplication.sharedApplication()
            existing = nsapp.delegate()
            self._reopen_delegate = _ReopenDelegate.alloc().init()

            # Method swizzling via category not needed — just add the method to existing delegate class
            if existing is not None:
                # Add method to existing delegate's class
                from objc import selector
                sel_name = "applicationShouldHandleReopen:hasVisibleWindows:"
                def _handler(self, app, has_visible):
                    try:
                        _on_settings()
                    except Exception:
                        pass
                    return False
                try:
                    existing.__class__.applicationShouldHandleReopen_hasVisibleWindows_ = _handler
                except Exception:
                    pass
        except Exception:
            pass

    def stop(self) -> None:
        try:
            import rumps
            rumps.quit_application()
        except Exception:
            pass


class _WinTray:
    """Windows tray using pystray."""

    def __init__(self, on_toggle, on_settings, on_quit, is_active):
        from PIL import Image

        self._on_toggle = on_toggle
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._is_active = is_active
        self._icon = None
        icon_path = config.MODULE_DIR.parent / "icon.png"
        try:
            self._image = Image.open(str(icon_path)).resize((64, 64), Image.LANCZOS)
        except Exception:
            self._image = self._create_fallback_icon()

    @staticmethod
    def _create_fallback_icon(size=64):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, size - 4, size - 4], fill="#43A047")
        return img

    def run(self) -> None:
        from pystray import Icon, Menu, MenuItem

        menu = Menu(
            MenuItem(
                lambda _: "Pause" if self._is_active() else "Resume",
                self._on_toggle,
            ),
            MenuItem("Settings", self._on_settings),
            Menu.SEPARATOR,
            MenuItem("Quit", self._on_quit),
        )
        self._icon = Icon(
            name=config.APP_NAME,
            icon=self._image,
            title=f"{config.APP_NAME} - Hold hotkey to record",
            menu=menu,
        )
        self._icon.run()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()


class TrayApp:
    """Cross-platform tray wrapper."""

    def __init__(self, on_toggle, on_settings, on_quit, is_active):
        self._impl = _create_tray(on_toggle, on_settings, on_quit, is_active)

    def run(self) -> None:
        self._impl.run()

    def stop(self) -> None:
        self._impl.stop()
