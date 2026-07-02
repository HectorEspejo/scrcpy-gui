# scrcpy-tray

A small **system-tray launcher for [scrcpy](https://github.com/Genymobile/scrcpy)**,
tuned for **KDE Plasma** but working on Ubuntu/Debian and any Linux desktop with a
system-tray host. It puts a persistent scrcpy icon in the panel from which you can
mirror any connected Android device in a couple of clicks — no terminal needed.

## Features

- **Device menu** with live hotplug detection (via `adb track-devices`, falling
  back to polling). USB and Wi-Fi (TCP/IP) devices, with unauthorized/offline
  states shown but disabled.
- **One-click launch** of `scrcpy -s <serial>` per device.
- **Presets**, remembered across launches: fullscreen, no-audio, no-control,
  turn screen off, keep awake, power-off-on-close, max size, bitrate, max FPS,
  codec (h264/h265/av1) and record-to-folder.
- **Wireless debugging window**: **pair** (Android 11+, with pairing code) and
  **connect** over TCP/IP, plus a **Restart adb** action.
- **Mirroring state** per device with a **Stop** action.
- **Desktop notifications** on connect/disconnect and launch failures.
- **Start on login** toggle (freedesktop autostart).

## Why Qt / QSystemTrayIcon

KDE's system tray speaks the **StatusNotifierItem (SNI)** D-Bus protocol. Qt6's
`QSystemTrayIcon` implements SNI natively, so the icon and menus work **identically
on Plasma X11 and Wayland** (the old GtkStatusIcon/XEmbed tray does not work on
Plasma 6 or Wayland at all).

## Requirements

- `python3` (>= 3.11)
- **PySide6** (`python3-pyside6.*` on Debian/Ubuntu, or `pip install PySide6`)
- `tomli-w` (`python3-tomli-w`)
- **scrcpy** and **adb** on `PATH` (`scrcpy`, `adb` / `android-tools-adb`)
- Optional: `wmctrl` (best-effort "Focus window" on X11)

> **GNOME note:** GNOME has no SNI host by default — install the
> *"AppIndicator and KStatusNotifierItem Support"* extension. On **KDE Plasma**
> nothing extra is needed.

## Run from source

```sh
cd scrcpy-tray
python3 -m scrcpy_tray
```

## Install

System-wide (installs the launcher, `.desktop` and a themed SVG icon):

```sh
sudo make install          # or: ./install.sh
```

Per-user, no root (into `~/.local`):

```sh
make install-user          # or: ./install.sh --user
```

Enable start-on-login (also toggleable from the tray menu):

```sh
make autostart
```

### Build a .deb (Debian/Ubuntu/KDE Neon/Kubuntu)

```sh
sudo apt build-dep .        # or install debhelper, dpkg-dev
dpkg-buildpackage -us -uc -b
sudo apt install ../scrcpy-tray_0.1.0_all.deb
```

## Configuration

Settings live in `~/.config/scrcpy-tray/config.toml` (created on first change).
Everything is editable from the tray menu; the file is human-editable too. Useful
keys: `poll_interval_ms`, `use_track_devices`, `notifications`, `stop_on_quit`,
and `scrcpy_path` / `adb_path` overrides if the binaries are in a non-standard
location.

## License

Apache-2.0 (matches scrcpy). The tray icon is derived from scrcpy's `scrcpy.svg`.
