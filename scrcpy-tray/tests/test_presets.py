from scrcpy_tray.presets import PresetState


def test_defaults_produce_no_args():
    assert PresetState().to_args() == []


def test_boolean_toggles():
    p = PresetState(
        fullscreen=True,
        no_audio=True,
        no_control=True,
        turn_screen_off=True,
        stay_awake=True,
        power_off_on_close=True,
    )
    args = p.to_args()
    for flag in (
        "--fullscreen",
        "--no-audio",
        "--no-control",
        "--turn-screen-off",
        "--stay-awake",
        "--power-off-on-close",
    ):
        assert flag in args


def test_value_flags():
    p = PresetState(max_size=1024, video_bit_rate="8M", max_fps=60, video_codec="h265")
    args = p.to_args()
    assert args[args.index("--max-size") + 1] == "1024"
    assert args[args.index("--video-bit-rate") + 1] == "8M"
    assert args[args.index("--max-fps") + 1] == "60"
    assert args[args.index("--video-codec") + 1] == "h265"


def test_zero_and_empty_values_are_omitted():
    p = PresetState(max_size=0, video_bit_rate="", max_fps=0, video_codec="")
    assert p.to_args() == []


def test_record_with_timestamp():
    p = PresetState(record_dir="/tmp/rec")
    args = p.to_args(record_timestamp="20260101-120000")
    assert args[args.index("--record") + 1] == "/tmp/rec/scrcpy-20260101-120000.mp4"


def test_record_omitted_without_timestamp():
    assert "--record" not in PresetState(record_dir="/tmp/rec").to_args()


def test_dict_roundtrip():
    p = PresetState(fullscreen=True, max_size=640, video_codec="av1")
    assert PresetState.from_dict(p.to_dict()) == p


def test_from_dict_ignores_unknown_keys():
    p = PresetState.from_dict({"fullscreen": True, "bogus": 123})
    assert p.fullscreen is True
