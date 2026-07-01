"""Launch presets and their mapping to scrcpy CLI flags."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, fields

# Choices offered in the exclusive submenus. The first entry of each is the
# scrcpy default ("no flag"), represented by 0 / empty string.
MAX_SIZE_CHOICES: tuple[int, ...] = (0, 640, 1024, 1280, 1920)
BITRATE_CHOICES: tuple[str, ...] = ("", "2M", "4M", "8M", "16M")
FPS_CHOICES: tuple[int, ...] = (0, 30, 60, 120)
CODEC_CHOICES: tuple[str, ...] = ("", "h264", "h265", "av1")


@dataclass
class PresetState:
    """User-selected launch options, persisted and applied to every launch."""

    fullscreen: bool = False
    no_audio: bool = False
    no_control: bool = False
    turn_screen_off: bool = False
    stay_awake: bool = False
    power_off_on_close: bool = False
    max_size: int = 0
    video_bit_rate: str = ""
    max_fps: int = 0
    video_codec: str = ""
    record_dir: str = ""

    def to_args(self, record_timestamp: str | None = None) -> list[str]:
        """Build the scrcpy argument list for these presets.

        ``record_timestamp`` is only used when ``record_dir`` is set; the caller
        (the launcher) passes a stable timestamp so the recording filename is
        deterministic for a given launch.
        """
        args: list[str] = []
        if self.fullscreen:
            args.append("--fullscreen")
        if self.no_audio:
            args.append("--no-audio")
        if self.no_control:
            args.append("--no-control")
        if self.turn_screen_off:
            args.append("--turn-screen-off")
        if self.stay_awake:
            args.append("--stay-awake")
        if self.power_off_on_close:
            args.append("--power-off-on-close")
        if self.max_size > 0:
            args += ["--max-size", str(self.max_size)]
        if self.video_bit_rate:
            args += ["--video-bit-rate", self.video_bit_rate]
        if self.max_fps > 0:
            args += ["--max-fps", str(self.max_fps)]
        if self.video_codec:
            args += ["--video-codec", self.video_codec]
        if self.record_dir and record_timestamp:
            target = os.path.join(
                os.path.expanduser(self.record_dir), f"scrcpy-{record_timestamp}.mp4"
            )
            args += ["--record", target]
        return args

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PresetState":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})
