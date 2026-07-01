"""Application bootstrap: wires adb discovery, launcher, tray and notifications."""

from __future__ import annotations

import sys

from PySide6.QtCore import QDeadlineTimer, QThread, QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from . import APP_ID, APP_NAME, DISPLAY_NAME, paths
from .adb import AdbClient, AdbTracker
from .launcher import ScrcpyLauncher
from .notify import Notifier
from .settings import Settings
from .tray import TrayIcon


def _wait_for_tray(timeout_ms: int = 15000) -> bool:
    """Wait for an SNI host to appear (autostart can beat plasmashell)."""
    deadline = QDeadlineTimer(timeout_ms)
    while not QSystemTrayIcon.isSystemTrayAvailable():
        if deadline.hasExpired():
            return False
        QApplication.processEvents()
        QThread.msleep(200)
    return True


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(DISPLAY_NAME)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)

    settings = Settings.load()

    adb = AdbClient(paths.find_executable("adb", settings.adb_path))
    launcher = ScrcpyLauncher(paths.find_executable("scrcpy", settings.scrcpy_path))
    notifier = Notifier(enabled=settings.notifications)

    if not _wait_for_tray():
        print(
            "scrcpy-tray: no system tray available. On KDE this is plasmashell; "
            "on GNOME install the AppIndicator/KStatusNotifierItem extension.",
            file=sys.stderr,
        )

    tray = TrayIcon(settings, adb, launcher, notifier, on_quit=app.quit)
    notifier.set_tray(tray)
    tray.show()

    adb.message.connect(lambda msg: notifier.info("adb", msg))
    adb.error.connect(lambda msg: notifier.warn("adb", msg))

    # --- device discovery: track-devices (event-driven) with poll fallback
    poll = QTimer()
    poll.setInterval(max(1000, settings.poll_interval_ms))
    poll.timeout.connect(adb.list_devices)

    tracker = AdbTracker()
    tracker.changed.connect(adb.list_devices)

    def on_tracker_failed(_reason: str) -> None:
        if not poll.isActive():
            poll.start()

    tracker.failed.connect(on_tracker_failed)

    def begin_discovery() -> None:
        adb.list_devices()
        if settings.use_track_devices:
            tracker.start()
        else:
            poll.start()

    if adb.available:
        # Make sure the adb server is up before opening the track-devices socket.
        adb.start_server(begin_discovery)
    else:
        notifier.warn(
            "adb not found",
            "Install android-tools-adb (or set adb_path in the config).",
        )
        adb.list_devices()  # emits [] so the menu shows the right message

    if not launcher.available:
        notifier.warn(
            "scrcpy not found",
            "Install scrcpy (or set scrcpy_path in the config).",
        )

    def on_quit() -> None:
        tracker.stop()
        poll.stop()
        if settings.stop_on_quit:
            launcher.stop_all()

    app.aboutToQuit.connect(on_quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
