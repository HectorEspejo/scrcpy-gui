PREFIX ?= /usr
DESTDIR ?=

BINDIR  = $(PREFIX)/bin
LIBDIR  = $(PREFIX)/lib/scrcpy-tray
DATADIR = $(PREFIX)/share
APPDIR  = $(DATADIR)/applications
ICONDIR = $(DATADIR)/icons/hicolor/scalable/apps

.PHONY: install install-user autostart uninstall test clean

install:
	install -d $(DESTDIR)$(LIBDIR)/scrcpy_tray
	cp -r src/scrcpy_tray/. $(DESTDIR)$(LIBDIR)/scrcpy_tray/
	find $(DESTDIR)$(LIBDIR)/scrcpy_tray -name __pycache__ -type d -prune -exec rm -rf {} +
	install -d $(DESTDIR)$(LIBDIR)/scrcpy_tray/data
	install -m644 data/scrcpy-tray.svg $(DESTDIR)$(LIBDIR)/scrcpy_tray/data/scrcpy-tray.svg
	install -m644 data/disconnected.png $(DESTDIR)$(LIBDIR)/scrcpy_tray/data/disconnected.png
	install -d $(DESTDIR)$(BINDIR)
	sed 's|@LIBDIR@|$(LIBDIR)|g' data/launcher.sh.in > $(DESTDIR)$(BINDIR)/scrcpy-tray
	chmod 755 $(DESTDIR)$(BINDIR)/scrcpy-tray
	install -d $(DESTDIR)$(APPDIR)
	install -m644 data/scrcpy-tray.desktop $(DESTDIR)$(APPDIR)/scrcpy-tray.desktop
	install -d $(DESTDIR)$(ICONDIR)
	install -m644 data/scrcpy-tray.svg $(DESTDIR)$(ICONDIR)/scrcpy-tray.svg
	@if [ -z "$(DESTDIR)" ]; then \
		command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database $(APPDIR) || true; \
		command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f $(DATADIR)/icons/hicolor || true; \
	fi
	@echo "Installed scrcpy-tray to $(PREFIX). Run: scrcpy-tray"

install-user:
	$(MAKE) install PREFIX=$(HOME)/.local
	@echo "If '$(HOME)/.local/bin' is not on your PATH, add it to run 'scrcpy-tray'."

autostart:
	install -d $(HOME)/.config/autostart
	install -m644 data/scrcpy-tray.desktop $(HOME)/.config/autostart/scrcpy-tray.desktop
	@echo "Enabled autostart on login."

uninstall:
	rm -rf $(DESTDIR)$(LIBDIR)
	rm -f $(DESTDIR)$(BINDIR)/scrcpy-tray
	rm -f $(DESTDIR)$(APPDIR)/scrcpy-tray.desktop
	rm -f $(DESTDIR)$(ICONDIR)/scrcpy-tray.svg

test:
	python3 -m pytest -q

clean:
	find src -name '__pycache__' -type d -prune -exec rm -rf {} +
