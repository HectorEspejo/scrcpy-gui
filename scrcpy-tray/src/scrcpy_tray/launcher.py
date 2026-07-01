"""Launches and tracks one scrcpy process per device serial."""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, Signal

from .adb import process_environment
from .device import Device

_ERROR_TEXT = {
    QProcess.ProcessError.FailedToStart: "could not start scrcpy (not found or not executable)",
    QProcess.ProcessError.Crashed: "scrcpy crashed",
    QProcess.ProcessError.Timedout: "scrcpy timed out",
    QProcess.ProcessError.WriteError: "write error talking to scrcpy",
    QProcess.ProcessError.ReadError: "read error talking to scrcpy",
}


class ScrcpyLauncher(QObject):
    """Owns a ``QProcess`` per running serial so we can track and stop them.

    Uses non-detached processes on purpose: this is what lets the tray show a
    "mirroring…" state, offer a Stop action, and report crashes.
    """

    started = Signal(str)          # serial
    stopped = Signal(str, int)     # serial, exit code
    failed = Signal(str, str)      # serial, human-readable message

    def __init__(self, scrcpy_path: str | None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._scrcpy = scrcpy_path
        self._env = process_environment()
        self._procs: dict[str, QProcess] = {}

    @property
    def available(self) -> bool:
        return bool(self._scrcpy)

    def set_scrcpy_path(self, path: str | None) -> None:
        self._scrcpy = path

    def is_running(self, serial: str) -> bool:
        return serial in self._procs

    def running_serials(self) -> list[str]:
        return list(self._procs)

    def launch(self, device: Device, extra_args: list[str]) -> None:
        if not self._scrcpy:
            self.failed.emit(device.serial, "scrcpy not found on PATH")
            return
        if self.is_running(device.serial):
            return
        serial = device.serial
        proc = QProcess(self)
        proc.setProcessEnvironment(self._env)
        proc.started.connect(lambda s=serial: self.started.emit(s))
        proc.errorOccurred.connect(lambda err, s=serial: self._on_error(s, err))
        proc.finished.connect(lambda code, _st, s=serial: self._on_finished(s, code))
        args = ["-s", serial, "--window-title", f"scrcpy — {device.label}", *extra_args]
        self._procs[serial] = proc
        proc.start(self._scrcpy, args)

    def stop(self, serial: str) -> None:
        proc = self._procs.get(serial)
        if proc is not None:
            proc.terminate()  # SIGTERM — scrcpy shuts down cleanly

    def stop_all(self) -> None:
        for proc in list(self._procs.values()):
            proc.terminate()

    def _on_error(self, serial: str, err: QProcess.ProcessError) -> None:
        proc = self._procs.pop(serial, None)
        if proc is not None:
            proc.deleteLater()
        self.failed.emit(serial, _ERROR_TEXT.get(err, "scrcpy error"))

    def _on_finished(self, serial: str, code: int) -> None:
        proc = self._procs.pop(serial, None)
        if proc is None:
            return  # already handled by _on_error (e.g. failed to start)
        stderr = bytes(proc.readAllStandardError().data()).decode(errors="replace").strip()
        proc.deleteLater()
        if code != 0:
            tail = stderr[-400:] if stderr else f"scrcpy exited with code {code}"
            self.failed.emit(serial, tail)
        self.stopped.emit(serial, code)
