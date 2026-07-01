"""Persisted settings, stored as human-editable TOML under XDG config.

The concrete storage backend is intentionally isolated behind :class:`Settings`
so it can be swapped (e.g. to QSettings) without touching the rest of the app.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

from . import paths
from .presets import PresetState


@dataclass
class Settings:
    presets: PresetState = field(default_factory=PresetState)
    default_device: str = ""
    poll_interval_ms: int = 4000
    use_track_devices: bool = True
    notifications: bool = True
    stop_on_quit: bool = False
    scrcpy_path: str = ""
    adb_path: str = ""

    # --- serialization ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "default_device": self.default_device,
            "poll_interval_ms": self.poll_interval_ms,
            "use_track_devices": self.use_track_devices,
            "notifications": self.notifications,
            "stop_on_quit": self.stop_on_quit,
            "scrcpy_path": self.scrcpy_path,
            "adb_path": self.adb_path,
            "presets": self.presets.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        data = data or {}
        top = {
            k: data[k]
            for k in (
                "default_device",
                "poll_interval_ms",
                "use_track_devices",
                "notifications",
                "stop_on_quit",
                "scrcpy_path",
                "adb_path",
            )
            if k in data
        }
        return cls(presets=PresetState.from_dict(data.get("presets", {})), **top)

    # --- disk I/O ---------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or paths.config_file()
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except (FileNotFoundError, tomllib.TOMLDecodeError):
            return cls()
        return cls.from_dict(data)

    def save(self, path: Path | None = None) -> None:
        path = path or paths.config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            tomli_w.dump(self.to_dict(), fh)
