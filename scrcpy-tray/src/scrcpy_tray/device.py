"""Android device model and parsing of ``adb devices -l`` output."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Device:
    """A single Android device as reported by adb.

    ``state`` mirrors adb's connection state: ``device`` (ready), ``unauthorized``
    (needs the "Allow USB debugging" confirmation), ``offline``, ``no permissions``,
    etc. Only ``device`` is launchable.
    """

    serial: str
    state: str
    model: str | None = None
    product: str | None = None
    transport_id: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        """True when scrcpy can actually mirror this device."""
        return self.state == "device"

    @property
    def is_wireless(self) -> bool:
        """True for TCP/IP devices, whose serial looks like ``host:port``."""
        host, sep, port = self.serial.rpartition(":")
        return bool(sep) and host != "" and port.isdigit()

    @property
    def pretty_model(self) -> str | None:
        """Model with adb's underscores turned back into spaces (``Pixel_7``)."""
        if not self.model:
            return None
        return self.model.replace("_", " ")

    @property
    def label(self) -> str:
        """Human-friendly label for menus and window titles."""
        name = self.pretty_model or self.serial
        parts = [name]
        if self.is_wireless and self.pretty_model:
            parts.append("(wifi)")
        if not self.usable:
            parts.append(f"— {self.state}")
        elif self.pretty_model and self.pretty_model != self.serial:
            # Disambiguate two devices of the same model by short serial.
            pass
        return " ".join(parts)


# Lines that adb emits which are not device rows.
_SKIP_PREFIXES = ("*", "adb server", "adb: ", "List of devices")


def parse_devices(text: str) -> list[Device]:
    """Parse the output of ``adb devices -l`` into a list of :class:`Device`.

    Example line::

        192.168.1.5:5555  device product:redfin model:Pixel_5 transport_id:3

    The first line ("List of devices attached") and any adb daemon chatter
    (lines starting with ``*``) are ignored. Robust to both ``adb devices`` and
    ``adb devices -l`` output.
    """
    devices: list[Device] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in _SKIP_PREFIXES):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        kv: dict[str, str] = {}
        for token in parts[2:]:
            key, sep, value = token.partition(":")
            if sep and key:
                kv[key] = value
        devices.append(
            Device(
                serial=serial,
                state=state,
                model=kv.pop("model", None),
                product=kv.pop("product", None),
                transport_id=kv.pop("transport_id", None),
                extra=kv,
            )
        )
    return devices
