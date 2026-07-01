"""Start-on-login support via the freedesktop autostart spec.

Writes/removes ``~/.config/autostart/scrcpy-tray.desktop`` (honoured by both KDE
and GNOME). Prefers the installed ``scrcpy-tray`` console script so autostart is
independent of any virtualenv; falls back to ``python -m scrcpy_tray``.
"""

from __future__ import annotations

import shutil
import sys

from . import DISPLAY_NAME, paths


def _exec_command() -> str:
    installed = shutil.which("scrcpy-tray", path=paths.augmented_path())
    if installed:
        return installed
    return f"{sys.executable} -m scrcpy_tray"


def _desktop_contents() -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={DISPLAY_NAME}\n"
        "Comment=Launch scrcpy from the system tray\n"
        f"Exec={_exec_command()}\n"
        "Icon=scrcpy-tray\n"
        "Terminal=false\n"
        "Categories=Utility;RemoteAccess;\n"
        "X-GNOME-Autostart-enabled=true\n"
        "X-KDE-autostart-after=panel\n"
    )


def is_enabled() -> bool:
    return paths.autostart_file().exists()


def enable() -> None:
    target = paths.autostart_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_desktop_contents(), encoding="utf-8")


def disable() -> None:
    paths.autostart_file().unlink(missing_ok=True)


def set_enabled(enabled: bool) -> None:
    enable() if enabled else disable()
