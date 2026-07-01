#!/bin/sh
# Friendly wrapper around the Makefile.
#   ./install.sh            system-wide install (uses sudo if not root)
#   ./install.sh --user     install into ~/.local (no root)
#   ./install.sh --uninstall
set -e
cd "$(dirname "$0")"

case "${1:-}" in
    --user)
        exec make install-user
        ;;
    --uninstall)
        if [ "$(id -u)" -eq 0 ]; then exec make uninstall; else exec sudo make uninstall; fi
        ;;
    "")
        if [ "$(id -u)" -eq 0 ]; then exec make install; else exec sudo make install; fi
        ;;
    *)
        echo "usage: ./install.sh [--user|--uninstall]" >&2
        exit 1
        ;;
esac
