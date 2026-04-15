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
        self._app = rumps.App(config.APP_NAME, title=None, icon=icon_path, template=True)

    def run(self) -> None:
        import rumps

        @rumps.clicked("Pause / Resume")
        def toggle(_):
            self._on_toggle()

        @rumps.clicked("Control Panel")
        def settings(_):
            self._on_settings()

        @rumps.clicked("Quit")
        def quit_app(_):
            self._on_quit()
            rumps.quit_application()

        self._app.menu = ["Pause / Resume", "Control Panel", None, "Quit"]
        self._app.run()

    def stop(self) -> None:
        try:
            import rumps
            rumps.quit_application()
        except Exception:
            pass


class _WinTray:
    """Windows tray using pystray."""

    def __init__(self, on_toggle, on_settings, on_quit, is_active):
        from PIL import Image, ImageDraw

        self._on_toggle = on_toggle
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._is_active = is_active
        self._icon = None
        self._image = self._create_icon()

    def _create_icon(self, color="#43A047", size=64):
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, size - 4, size - 4], fill=color)
        cx, cy = size // 2, size // 2
        r = size // 6
        draw.rounded_rectangle(
            [cx - r, cy - r - 4, cx + r, cy + r + 2], radius=r, fill="white"
        )
        draw.rectangle([cx - 1, cy + r + 2, cx + 1, cy + r + 10], fill="white")
        draw.arc(
            [cx - r - 4, cy - 2, cx + r + 4, cy + r + 8],
            start=0, end=180, fill="white", width=2,
        )
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
