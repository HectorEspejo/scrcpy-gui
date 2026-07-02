"""Dialog windows for the tray app (wireless pair/connect)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .adb import AdbClient


class WirelessDialog(QDialog):
    """Pair (Android 11+) and connect to a device over TCP/IP.

    Android wireless debugging is two steps with *different* ports: pair once
    with the pairing address + 6-digit code, then connect using the device's
    main IP:port. This window exposes both, with inline success/error feedback.
    """

    def __init__(self, adb: AdbClient, parent=None) -> None:
        super().__init__(parent)
        self._adb = adb
        self.setWindowTitle("scrcpy tray — Wireless (TCP/IP)")
        self.setModal(False)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "On the phone: Developer options → Wireless debugging. Use "
            "“Pair device with pairing code” for the first step, then the "
            "device's IP address & port for the second."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # --- Pair ---------------------------------------------------------
        pair_box = QGroupBox("1. Pair a new device (Android 11+)")
        pg = QGridLayout(pair_box)
        self._pair_addr = QLineEdit()
        self._pair_addr.setPlaceholderText("192.168.1.5:37123  (pairing IP:port)")
        self._pair_code = QLineEdit()
        self._pair_code.setPlaceholderText("123456  (6-digit code)")
        self._pair_btn = QPushButton("Pair")
        pg.addWidget(QLabel("Pairing IP:port"), 0, 0)
        pg.addWidget(self._pair_addr, 0, 1)
        pg.addWidget(QLabel("Pairing code"), 1, 0)
        pg.addWidget(self._pair_code, 1, 1)
        pg.addWidget(self._pair_btn, 2, 1)
        layout.addWidget(pair_box)

        # --- Connect ------------------------------------------------------
        conn_box = QGroupBox("2. Connect")
        cg = QGridLayout(conn_box)
        self._conn_addr = QLineEdit()
        self._conn_addr.setPlaceholderText("192.168.1.5:5555  (device IP:port)")
        self._conn_btn = QPushButton("Connect")
        cg.addWidget(QLabel("Device IP:port"), 0, 0)
        cg.addWidget(self._conn_addr, 0, 1)
        cg.addWidget(self._conn_btn, 1, 1)
        layout.addWidget(conn_box)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(self._status.textInteractionFlags().TextSelectableByMouse)
        layout.addWidget(self._status)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        self._pair_btn.clicked.connect(self._do_pair)
        self._conn_btn.clicked.connect(self._do_connect)
        self._pair_code.returnPressed.connect(self._do_pair)
        self._conn_addr.returnPressed.connect(self._do_connect)

    # --- actions ----------------------------------------------------------

    def _do_pair(self) -> None:
        address = self._pair_addr.text().strip()
        code = self._pair_code.text().strip()
        if not address or not code:
            self._set_status("Enter the pairing IP:port and the 6-digit code.", error=True)
            return
        self._set_busy(True, "Pairing…")

        def done(ok: bool, text: str) -> None:
            self._set_busy(False)
            self._set_status(text, error=not ok)
            if ok and not self._conn_addr.text().strip():
                # Prefill the connect field with the host (the connect port
                # differs from the pairing port, so leave the port for the user).
                host = address.rsplit(":", 1)[0]
                self._conn_addr.setText(f"{host}:")
                self._conn_addr.setFocus()

        self._adb.pair(address, code, done)

    def _do_connect(self) -> None:
        address = self._conn_addr.text().strip()
        if not address:
            self._set_status("Enter the device IP:port.", error=True)
            return
        self._set_busy(True, "Connecting…")

        def done(ok: bool, text: str) -> None:
            self._set_busy(False)
            self._set_status(text, error=not ok)

        self._adb.connect_wireless(address, done)

    # --- helpers ----------------------------------------------------------

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._pair_btn.setEnabled(not busy)
        self._conn_btn.setEnabled(not busy)
        if message:
            self._set_status(message)

    def _set_status(self, text: str, error: bool = False) -> None:
        self._status.setStyleSheet("color: #c0392b;" if error else "color: #27ae60;")
        self._status.setText(text)
