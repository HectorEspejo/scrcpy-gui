"""adb integration: device listing/actions and event-driven hotplug tracking.

Two collaborators:

* :class:`AdbClient` runs ``adb`` as a non-blocking ``QProcess`` for
  ``devices -l``, ``connect`` and server restart, emitting the parsed device
  list.
* :class:`AdbTracker` speaks the adb host protocol directly over a socket
  (``host:track-devices`` on tcp 5037) so the menu updates the instant a device
  is plugged/unplugged — with automatic fallback to polling if the socket fails.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal
from PySide6.QtNetwork import QTcpSocket

from . import paths
from .device import Device, parse_devices


def process_environment() -> QProcessEnvironment:
    """A child-process environment with a PATH that can actually find adb/scrcpy."""
    env = QProcessEnvironment.systemEnvironment()
    env.insert("PATH", paths.augmented_path())
    return env


class AdbClient(QObject):
    """Runs adb commands asynchronously and reports the device list."""

    devices_changed = Signal(list)  # list[Device]
    message = Signal(str)
    error = Signal(str)

    def __init__(self, adb_path: str | None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._adb = adb_path
        self._env = process_environment()
        self._list_proc: QProcess | None = None
        self._task_procs: list[QProcess] = []

    @property
    def available(self) -> bool:
        return bool(self._adb)

    def set_adb_path(self, path: str | None) -> None:
        self._adb = path

    # --- device listing ---------------------------------------------------

    def list_devices(self) -> None:
        if not self._adb:
            self.devices_changed.emit([])
            return
        if self._list_proc is not None:
            return  # a listing is already in flight; its result will refresh us
        proc = QProcess(self)
        proc.setProcessEnvironment(self._env)
        proc.finished.connect(lambda _c, _s, p=proc: self._on_list_finished(p))
        proc.errorOccurred.connect(lambda _e, p=proc: self._on_list_error(p))
        self._list_proc = proc
        proc.start(self._adb, ["devices", "-l"])

    def _on_list_finished(self, proc: QProcess) -> None:
        if proc is not self._list_proc:
            return
        out = bytes(proc.readAllStandardOutput().data()).decode(errors="replace")
        self._list_proc = None
        proc.deleteLater()
        self.devices_changed.emit(parse_devices(out))

    def _on_list_error(self, proc: QProcess) -> None:
        if proc is not self._list_proc:
            return
        err = proc.errorString()
        self._list_proc = None
        proc.deleteLater()
        self.error.emit(f"adb error: {err}")
        self.devices_changed.emit([])

    # --- one-shot commands ------------------------------------------------

    def _run(self, args: list[str], on_done=None) -> None:
        if not self._adb:
            self.error.emit("adb not found")
            return
        proc = QProcess(self)
        proc.setProcessEnvironment(self._env)
        self._task_procs.append(proc)

        def finished(code, _status, p=proc):
            out = bytes(p.readAllStandardOutput().data()).decode(errors="replace").strip()
            err = bytes(p.readAllStandardError().data()).decode(errors="replace").strip()
            if p in self._task_procs:
                self._task_procs.remove(p)
            p.deleteLater()
            if on_done is not None:
                on_done(code, out, err)

        def errored(_e, p=proc):
            if p in self._task_procs:
                self._task_procs.remove(p)
            msg = p.errorString()
            p.deleteLater()
            self.error.emit(f"adb error: {msg}")

        proc.finished.connect(finished)
        proc.errorOccurred.connect(errored)
        proc.start(self._adb, args)

    def start_server(self, on_done=None) -> None:
        self._run(["start-server"], lambda _c, _o, _e: on_done() if on_done else None)

    def connect_wireless(self, address: str) -> None:
        def done(_code, out, err):
            self.message.emit(out or err or f"adb connect {address}")
            self.list_devices()

        self._run(["connect", address], done)

    def restart(self) -> None:
        def after_kill(_c, _o, _e):
            def after_start(_c2, _o2, _e2):
                self.message.emit("adb server restarted")
                self.list_devices()

            self._run(["start-server"], after_start)

        self._run(["kill-server"], after_kill)


class AdbTracker(QObject):
    """Event-driven device tracking via the adb ``host:track-devices`` stream.

    Emits :attr:`changed` on every device-list change (the caller then re-lists
    with ``-l`` to get model info). On any socket problem it emits :attr:`failed`
    so the app can fall back to timer polling.
    """

    changed = Signal()
    failed = Signal(str)

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5037,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._port = port
        self._running = False
        self._got_okay = False
        self._buf = bytearray()
        self._sock = QTcpSocket(self)
        self._sock.connected.connect(self._on_connected)
        self._sock.readyRead.connect(self._on_ready_read)
        self._sock.errorOccurred.connect(self._on_error)
        self._sock.disconnected.connect(self._on_disconnected)

    def start(self) -> None:
        self._running = True
        self._got_okay = False
        self._buf.clear()
        self._sock.abort()
        self._sock.connectToHost(self._host, self._port)

    def stop(self) -> None:
        self._running = False
        self._sock.abort()

    def _on_connected(self) -> None:
        request = b"host:track-devices"
        self._sock.write(b"%04x" % len(request) + request)

    def _on_ready_read(self) -> None:
        self._buf += bytes(self._sock.readAll().data())
        self._process()

    def _process(self) -> None:
        if not self._got_okay:
            if len(self._buf) < 4:
                return
            status = bytes(self._buf[:4])
            del self._buf[:4]
            if status != b"OKAY":
                self._fail("adb rejected track-devices")
                return
            self._got_okay = True
        # Stream of length-prefixed snapshots; one arrives on every change.
        while len(self._buf) >= 4:
            try:
                length = int(bytes(self._buf[:4]).decode("ascii"), 16)
            except ValueError:
                self._fail("malformed adb protocol framing")
                return
            if len(self._buf) < 4 + length:
                return
            del self._buf[: 4 + length]
            self.changed.emit()

    def _on_error(self, _err) -> None:
        if self._running:
            self._fail(self._sock.errorString())

    def _on_disconnected(self) -> None:
        if self._running:
            self._fail("adb track-devices connection closed")

    def _fail(self, message: str) -> None:
        if not self._running:
            return
        self._running = False
        self._sock.abort()
        self.failed.emit(message)
