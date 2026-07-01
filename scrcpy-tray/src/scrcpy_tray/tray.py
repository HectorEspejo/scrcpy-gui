"""The system-tray icon and its dynamic context menu."""

from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import QProcess
from PySide6.QtGui import QAction, QActionGroup, QCursor, QIcon
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QSystemTrayIcon

from . import DISPLAY_NAME, autostart
from .adb import AdbClient
from .device import Device
from .launcher import ScrcpyLauncher
from .notify import Notifier
from .paths import asset_path
from .presets import (
    BITRATE_CHOICES,
    CODEC_CHOICES,
    FPS_CHOICES,
    MAX_SIZE_CHOICES,
)
from .settings import Settings


def _connected_icon() -> QIcon:
    themed = QIcon.fromTheme("scrcpy-tray")
    if not themed.isNull():
        return themed
    path = asset_path("icon")
    return QIcon(path) if path else QIcon()


def _disconnected_icon(fallback: QIcon) -> QIcon:
    path = asset_path("disconnected")
    return QIcon(path) if path else fallback


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        settings: Settings,
        adb: AdbClient,
        launcher: ScrcpyLauncher,
        notifier: Notifier,
        on_quit,
        parent=None,
    ) -> None:
        self._icon_connected = _connected_icon()
        self._icon_disconnected = _disconnected_icon(self._icon_connected)
        super().__init__(self._icon_disconnected, parent)

        self._settings = settings
        self._adb = adb
        self._launcher = launcher
        self._notifier = notifier
        self._on_quit = on_quit
        self._devices: list[Device] = []

        self._menu = QMenu()
        self._menu.aboutToShow.connect(self._rebuild)
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

        self._adb.devices_changed.connect(self._on_devices_changed)
        self._launcher.started.connect(self._on_launch_state)
        self._launcher.stopped.connect(self._on_launch_state)
        self._launcher.failed.connect(self._on_launch_failed)

        self._update_icon()
        self._rebuild()

    # --- model updates ----------------------------------------------------

    def _on_devices_changed(self, devices: list[Device]) -> None:
        old = {d.serial for d in self._devices if d.usable}
        new_labels = {d.serial: d.label for d in devices}
        old_labels = {d.serial: d.label for d in self._devices}
        new = {d.serial for d in devices if d.usable}
        for serial in sorted(new - old):
            self._notifier.info("Device connected", new_labels.get(serial, serial))
        for serial in sorted(old - new):
            self._notifier.info("Device disconnected", old_labels.get(serial, serial))
        self._devices = list(devices)
        self._update_icon()
        self._rebuild()

    def _on_launch_state(self, *_args) -> None:
        self._update_icon()
        self._rebuild()

    def _on_launch_failed(self, serial: str, message: str) -> None:
        label = next((d.label for d in self._devices if d.serial == serial), serial)
        self._notifier.error("scrcpy failed", f"{label}: {message}")
        self._update_icon()
        self._rebuild()

    def _update_icon(self) -> None:
        usable = sum(1 for d in self._devices if d.usable)
        self.setIcon(self._icon_connected if usable else self._icon_disconnected)
        running = len(self._launcher.running_serials())
        self.setToolTip(f"{DISPLAY_NAME} — {usable} device(s), {running} mirroring")

    # --- menu construction ------------------------------------------------

    def _rebuild(self) -> None:
        m = self._menu
        m.clear()

        header = m.addAction("Devices")
        header.setEnabled(False)
        if not self._adb.available:
            m.addAction("adb not found — install android-tools/adb").setEnabled(False)
        elif not self._devices:
            m.addAction("No devices connected").setEnabled(False)
        else:
            for device in self._devices:
                self._add_device_entry(m, device)

        m.addSeparator()
        m.addMenu(self._build_presets_menu())
        m.addSeparator()

        wifi = m.addAction("Wireless connect (TCP/IP)…")
        wifi.triggered.connect(self._wireless_dialog)
        wifi.setEnabled(self._adb.available)
        refresh = m.addAction("Refresh devices")
        refresh.triggered.connect(self._adb.list_devices)
        refresh.setEnabled(self._adb.available)
        restart = m.addAction("Restart adb")
        restart.triggered.connect(self._adb.restart)
        restart.setEnabled(self._adb.available)

        m.addSeparator()
        auto = m.addAction("Start on login")
        auto.setCheckable(True)
        auto.setChecked(autostart.is_enabled())
        auto.toggled.connect(self._toggle_autostart)

        m.addSeparator()
        m.addAction("Quit").triggered.connect(lambda _=False: self._on_quit())

    def _add_device_entry(self, menu: QMenu, device: Device) -> None:
        if not device.usable:
            act = menu.addAction(device.label)
            act.setEnabled(False)
            return
        if self._launcher.is_running(device.serial):
            sub = menu.addMenu(f"●  {device.label} — mirroring")
            focus = sub.addAction("Focus window")
            focus.triggered.connect(lambda _=False, d=device: self._focus(d))
            stop = sub.addAction("Stop")
            stop.triggered.connect(lambda _=False, s=device.serial: self._launcher.stop(s))
        else:
            act = menu.addAction(device.label)
            act.triggered.connect(lambda _=False, d=device: self._launch(d))

    def _build_presets_menu(self) -> QMenu:
        presets = self._settings.presets
        menu = QMenu("Presets")
        toggles = (
            ("Fullscreen", "fullscreen"),
            ("No audio", "no_audio"),
            ("No control (read-only)", "no_control"),
            ("Turn device screen off", "turn_screen_off"),
            ("Keep device awake", "stay_awake"),
            ("Power off device on close", "power_off_on_close"),
        )
        for label, attr in toggles:
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(getattr(presets, attr))
            act.toggled.connect(lambda checked, a=attr: self._set_toggle(a, checked))

        menu.addSeparator()
        menu.addMenu(self._choice_menu("Max size", "max_size", MAX_SIZE_CHOICES, _fmt_size))
        menu.addMenu(self._choice_menu("Bitrate", "video_bit_rate", BITRATE_CHOICES, _fmt_bitrate))
        menu.addMenu(self._choice_menu("Max FPS", "max_fps", FPS_CHOICES, _fmt_fps))
        menu.addMenu(self._choice_menu("Codec", "video_codec", CODEC_CHOICES, _fmt_codec))

        menu.addSeparator()
        rec = menu.addAction("Record to folder…")
        rec.setCheckable(True)
        rec.setChecked(bool(presets.record_dir))
        if presets.record_dir:
            rec.setToolTip(presets.record_dir)
        rec.triggered.connect(self._toggle_record)
        return menu

    def _choice_menu(self, title, attr, choices, fmt) -> QMenu:
        sub = QMenu(title)
        group = QActionGroup(sub)
        group.setExclusive(True)
        current = getattr(self._settings.presets, attr)
        for choice in choices:
            act = sub.addAction(fmt(choice))
            act.setCheckable(True)
            act.setChecked(choice == current)
            group.addAction(act)
            act.triggered.connect(lambda _=False, a=attr, v=choice: self._set_choice(a, v))
        return sub

    # --- actions ----------------------------------------------------------

    def _set_toggle(self, attr: str, checked: bool) -> None:
        setattr(self._settings.presets, attr, bool(checked))
        self._settings.save()

    def _set_choice(self, attr: str, value) -> None:
        setattr(self._settings.presets, attr, value)
        self._settings.save()

    def _toggle_record(self, checked: bool) -> None:
        if checked:
            folder = QFileDialog.getExistingDirectory(
                None, "Choose recording folder", os.path.expanduser("~")
            )
            self._settings.presets.record_dir = folder or ""
        else:
            self._settings.presets.record_dir = ""
        self._settings.save()

    def _launch(self, device: Device) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args = self._settings.presets.to_args(record_timestamp=timestamp)
        self._launcher.launch(device, args)
        self._settings.default_device = device.serial
        self._settings.save()

    def _focus(self, device: Device) -> None:
        # Best-effort raise; Wayland restricts activating external windows.
        QProcess.startDetached("wmctrl", ["-a", f"scrcpy — {device.label}"])

    def _wireless_dialog(self) -> None:
        text, ok = QInputDialog.getText(
            None, "Wireless connect", "Device address (ip:port):", text="192.168.1.:5555"
        )
        if ok and text.strip():
            self._adb.connect_wireless(text.strip())

    def _toggle_autostart(self, checked: bool) -> None:
        autostart.set_enabled(bool(checked))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        idle = [
            d for d in self._devices if d.usable and not self._launcher.is_running(d.serial)
        ]
        if len(idle) == 1:
            self._launch(idle[0])
        else:
            self._menu.popup(QCursor.pos())


# --- choice label formatting ----------------------------------------------

def _fmt_size(value: int) -> str:
    return "Unlimited" if value == 0 else f"{value} px"


def _fmt_bitrate(value: str) -> str:
    return "Default (8M)" if value == "" else value


def _fmt_fps(value: int) -> str:
    return "Unlimited" if value == 0 else f"{value} fps"


def _fmt_codec(value: str) -> str:
    return "Default (h264)" if value == "" else value
