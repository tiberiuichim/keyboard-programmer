#!/usr/bin/env bash
# Install the udev rule that lets you program the macropad without sudo/Docker.
# Idempotent: safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE="99-macropad.rules"
DEST="/etc/udev/rules.d/$RULE"

if [[ -e "$DEST" ]] && cmp -s "$HERE/$RULE" "$DEST"; then
    echo "udev rule already installed and up to date: $DEST"
else
    echo "Installing $RULE -> $DEST (needs root)"
    sudo cp "$HERE/$RULE" "$DEST"
fi

echo "Reloading udev..."
sudo udevadm control --reload
sudo udevadm trigger

echo
echo "Unplug and replug the pad, then run:  ./pad status"
echo
echo "If './pad status' still says access is denied, make sure you are in plugdev:"
echo "  sudo usermod -aG plugdev \$USER   # then log out and back in"
