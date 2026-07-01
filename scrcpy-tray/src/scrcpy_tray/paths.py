"""XDG paths, binary resolution and bundled-asset lookup.

Centralises two fiddly concerns:

* Where config / autostart files live (freedesktop XDG spec).
* Finding the ``adb`` and ``scrcpy`` executables. GUI/autostart processes often
  inherit a stripped ``PATH`` that misses ``~/.local/bin``, ``/snap/bin`` or the
  Android SDK ``platform-tools`` dir — the same reason scrcpy's own ``.desktop``
  launches through an interactive shell. We rebuild a sane search path instead.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import APP_NAME

# Extra directories that commonly hold adb/scrcpy but are missing from a
# GUI-launched process's PATH.
_EXTRA_BIN_DIRS = (
    "~/.local/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/snap/bin",
    "/var/lib/flatpak/exports/bin",
    "~/.local/share/flatpak/exports/bin",
    "/opt/homebrew/bin",  # macOS (Apple Silicon), harmless elsewhere
    "~/Android/Sdk/platform-tools",
    "~/Library/Android/sdk/platform-tools",
)


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


def config_file() -> Path:
    return config_dir() / "config.toml"


def autostart_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart"


def autostart_file() -> Path:
    return autostart_dir() / f"{APP_NAME}.desktop"


def augmented_path() -> str:
    """Return ``$PATH`` with common bin dirs appended (de-duplicated)."""
    entries: list[str] = []
    seen: set[str] = set()

    def add(directory: str) -> None:
        expanded = os.path.expanduser(directory)
        if expanded and expanded not in seen:
            seen.add(expanded)
            entries.append(expanded)

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        add(directory)
    for directory in _EXTRA_BIN_DIRS:
        add(directory)
    return os.pathsep.join(entries)


def find_executable(name: str, override: str | None = None) -> str | None:
    """Locate an executable, honouring an explicit config override first.

    Returns an absolute path, or ``None`` if not found. ``override`` may be a
    bare name (looked up on PATH) or an absolute path.
    """
    if override:
        candidate = os.path.expanduser(override)
        if os.path.isabs(candidate):
            return candidate if os.access(candidate, os.X_OK) else None
        found = shutil.which(candidate, path=augmented_path())
        if found:
            return found
    return shutil.which(name, path=augmented_path())


# --- Bundled assets ---------------------------------------------------------

_ASSET_NAMES = {
    "icon": "scrcpy-tray.svg",
    "disconnected": "disconnected.png",
}


def _asset_candidates(filename: str) -> list[Path]:
    here = Path(__file__).resolve()
    candidates = [
        # Running from a source checkout: scrcpy-tray/data/<file>
        here.parent.parent.parent / "data" / filename,
        # Running from an installed package next to a data/ dir.
        here.parent / "data" / filename,
    ]
    # System / user icon-theme locations (matches the Makefile install target).
    for prefix in (
        Path(os.environ.get("XDG_DATA_HOME", "")) if os.environ.get("XDG_DATA_HOME") else None,
        Path.home() / ".local" / "share",
        Path("/usr/local/share"),
        Path("/usr/share"),
    ):
        if prefix is None:
            continue
        candidates.append(prefix / "icons" / "hicolor" / "scalable" / "apps" / filename)
    return candidates


def asset_path(kind: str) -> str | None:
    """Absolute path to a bundled asset (``kind`` in ``icon``/``disconnected``)."""
    filename = _ASSET_NAMES[kind]
    for candidate in _asset_candidates(filename):
        if candidate.is_file():
            return str(candidate)
    return None
