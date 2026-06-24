#!/usr/bin/env bash
#
# One-time setup script for mousemaster-gw.
#
# This grants the current user write permission on /dev/uinput
# by adding them to the 'input' group.
#
# After running this script, you must log out and back in
# (or reboot) for the group change to take effect.
#

set -euo pipefail

echo "=== mousemaster-gw setup ==="
echo

# Check if uinput kernel module is available
if [ ! -c /dev/uinput ]; then
    echo "[1/3] Loading uinput kernel module..."
    sudo modprobe uinput 2>/dev/null || echo "  (module may already be loaded or built-in)"
else
    echo "[1/3] /dev/uinput exists"
fi

# Add user to input group
echo "[2/3] Adding user '$USER' to the 'input' group..."
if groups "$USER" | grep -q '\binput\b'; then
    echo "  User '$USER' is already in the 'input' group."
else
    sudo usermod -aG input "$USER"
    echo "  Added. You must log out and back in (or reboot) for this to take effect."
fi

# Verify PyGObject and dbus
echo "[3/3] Checking Python dependencies..."
PYTHON_OK=true

python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null || {
    echo "  WARNING: PyGObject (gi) not found."
    echo "  On Fedora: sudo dnf install python3-gobject python3-gi-cairo"
    echo "  On Ubuntu: sudo apt install python3-gi python3-gi-cairo"
    PYTHON_OK=false
}

python3 -c "import dbus" 2>/dev/null || {
    echo "  WARNING: python-dbus not found."
    echo "  On Fedora: sudo dnf install python3-dbus"
    echo "  On Ubuntu: sudo apt install python3-dbus"
    PYTHON_OK=false
}

if [ "$PYTHON_OK" = true ]; then
    echo "  All Python dependencies found."
fi

echo
echo "=== setup complete ==="
echo
echo "Next steps:"
echo "  1. Log out and back in (or reboot)"
echo "  2. Run ./start.sh"