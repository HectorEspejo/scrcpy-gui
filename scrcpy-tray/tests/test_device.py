from scrcpy_tray.device import parse_devices


def test_parse_basic_usb():
    out = (
        "List of devices attached\n"
        "0123456789ABCDEF       device product:sunfish model:Pixel_4a "
        "device:sunfish transport_id:1\n"
    )
    devs = parse_devices(out)
    assert len(devs) == 1
    d = devs[0]
    assert d.serial == "0123456789ABCDEF"
    assert d.state == "device"
    assert d.usable
    assert not d.is_wireless
    assert d.model == "Pixel_4a"
    assert d.pretty_model == "Pixel 4a"
    assert d.transport_id == "1"


def test_parse_wireless():
    out = (
        "List of devices attached\n"
        "192.168.1.5:5555   device product:redfin model:Pixel_5 transport_id:3\n"
    )
    d = parse_devices(out)[0]
    assert d.is_wireless
    assert d.usable
    assert "wifi" in d.label


def test_parse_unauthorized_and_offline():
    out = "List of devices attached\nABC123   unauthorized\nDEF456   offline\n"
    devs = parse_devices(out)
    assert [x.state for x in devs] == ["unauthorized", "offline"]
    assert not any(x.usable for x in devs)
    assert "unauthorized" in devs[0].label


def test_parse_skips_daemon_lines_and_blanks():
    out = (
        "* daemon not running; starting now at tcp:5037\n"
        "* daemon started successfully\n"
        "List of devices attached\n"
        "\n"
        "0123   device\n"
    )
    devs = parse_devices(out)
    assert len(devs) == 1
    assert devs[0].serial == "0123"


def test_parse_short_devices_output_without_l():
    # `adb devices` (no -l) has just serial + state.
    out = "List of devices attached\nemulator-5554\tdevice\n"
    d = parse_devices(out)[0]
    assert d.serial == "emulator-5554"
    assert d.model is None
    assert not d.is_wireless


def test_parse_empty():
    assert parse_devices("List of devices attached\n") == []
