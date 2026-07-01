"""Desktop notifications.

Routed through :meth:`QSystemTrayIcon.showMessage`, which on KDE/Plasma (and any
SNI host) is delivered by the ``org.freedesktop.Notifications`` service — so it
looks native with no extra dependency. Kept behind this small class so the rest
of the app calls semantic ``info``/``warn``/``error`` methods and a single
``enabled`` flag governs everything.

(Action buttons via a direct QtDBus ``Notify`` call are a possible future
enhancement; showMessage is the robust baseline.)
"""

from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon


class Notifier:
    def __init__(self, tray: QSystemTrayIcon | None = None, enabled: bool = True) -> None:
        self._tray = tray
        self.enabled = enabled

    def set_tray(self, tray: QSystemTrayIcon) -> None:
        self._tray = tray

    def info(self, title: str, body: str = "") -> None:
        self._show(title, body, QSystemTrayIcon.MessageIcon.Information)

    def warn(self, title: str, body: str = "") -> None:
        self._show(title, body, QSystemTrayIcon.MessageIcon.Warning)

    def error(self, title: str, body: str = "") -> None:
        self._show(title, body, QSystemTrayIcon.MessageIcon.Critical)

    def _show(self, title: str, body: str, icon: QSystemTrayIcon.MessageIcon) -> None:
        if not self.enabled or self._tray is None:
            return
        if not QSystemTrayIcon.supportsMessages():
            return
        self._tray.showMessage(title, body, icon, 5000)
