from scrcpy_tray.settings import Settings


def test_defaults():
    s = Settings()
    assert s.poll_interval_ms == 4000
    assert s.use_track_devices is True
    assert s.notifications is True
    assert s.presets.fullscreen is False


def test_roundtrip(tmp_path):
    s = Settings(default_device="ABC", stop_on_quit=True, adb_path="/opt/adb")
    s.presets.fullscreen = True
    s.presets.max_size = 1024
    s.presets.video_codec = "h265"
    path = tmp_path / "config.toml"
    s.save(path)

    loaded = Settings.load(path)
    assert loaded.default_device == "ABC"
    assert loaded.stop_on_quit is True
    assert loaded.adb_path == "/opt/adb"
    assert loaded.presets.fullscreen is True
    assert loaded.presets.max_size == 1024
    assert loaded.presets.video_codec == "h265"


def test_load_missing_returns_defaults(tmp_path):
    loaded = Settings.load(tmp_path / "does-not-exist.toml")
    assert loaded.default_device == ""
    assert loaded.presets.max_size == 0
